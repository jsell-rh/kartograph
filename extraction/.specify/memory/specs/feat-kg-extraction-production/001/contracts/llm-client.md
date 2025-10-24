# Contract: LLM Client Interface

## Purpose

Defines the boundary around LLM interactions to enable:

- **Transparent retries** with exponential backoff
- **Circuit breaker** patterns for rate limit handling
- **Cost tracking** and token usage monitoring
- **Testing** with mock implementations
- **Caching** of responses (future enhancement)
- **Rate limiting** to prevent quota exhaustion

## Interface Definition

### Core Protocol

```python
from typing import Protocol
from dataclasses import dataclass
from enum import Enum

class FinishReason(Enum):
    """Why the LLM stopped generating."""
    STOP = "stop"                    # Natural completion
    MAX_TOKENS = "max_tokens"        # Hit token limit
    ERROR = "error"                  # Error occurred

@dataclass(frozen=True)
class LLMRequest:
    """Immutable request to LLM."""
    system_prompt: str
    user_prompt: str
    model: str = "claude-sonnet-4-5@20250929"
    max_tokens: int = 4096
    temperature: float = 0.0  # Deterministic by default

    def __post_init__(self):
        """Validate request parameters."""
        if not self.system_prompt:
            raise ValueError("system_prompt cannot be empty")
        if not self.user_prompt:
            raise ValueError("user_prompt cannot be empty")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature must be between 0 and 1")

@dataclass(frozen=True)
class LLMResponse:
    """Immutable response from LLM."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: FinishReason

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

class LLMClient(Protocol):
    """
    Abstract interface for LLM interactions.

    This protocol defines the boundary around all LLM queries, enabling:
    - Testing with mocks
    - Retry logic with decorators
    - Cost tracking
    - Rate limiting
    - Caching
    """

    async def query(self, request: LLMRequest) -> LLMResponse:
        """
        Send query to LLM and return response.

        Args:
            request: The LLM request parameters

        Returns:
            The LLM response

        Raises:
            RateLimitError: When rate limit exceeded
            ContextLengthExceeded: When input too large
            LLMError: For other LLM errors
        """
        ...

    async def query_structured(
        self,
        request: LLMRequest,
        schema: type[BaseModel],
    ) -> tuple[BaseModel, LLMResponse]:
        """
        Send query and parse response into structured format.

        Args:
            request: The LLM request parameters
            schema: Pydantic model to parse response into

        Returns:
            Tuple of (parsed_object, raw_response)

        Raises:
            ValidationError: When response doesn't match schema
            RateLimitError: When rate limit exceeded
            ContextLengthExceeded: When input too large
            LLMError: For other LLM errors
        """
        ...
```

### Exception Hierarchy

```python
class LLMError(Exception):
    """Base class for all LLM errors."""
    pass

class RateLimitError(LLMError):
    """Rate limit exceeded. Should retry with backoff."""

    def __init__(self, retry_after_seconds: int | None = None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded. Retry after {retry_after_seconds}s")

class ContextLengthExceeded(LLMError):
    """Input exceeds context window. Should reduce input size."""

    def __init__(self, tokens_sent: int, max_tokens: int):
        self.tokens_sent = tokens_sent
        self.max_tokens = max_tokens
        super().__init__(
            f"Context length exceeded: {tokens_sent} > {max_tokens}"
        )

class AuthenticationError(LLMError):
    """Authentication failed. Check credentials."""
    pass

class InvalidRequestError(LLMError):
    """Request malformed. Fix request parameters."""
    pass
```

## Implementations

### Production Implementation

```python
from anthropic import Anthropic
from anthropic.vertex import AnthropicVertex
from kg_extractor.config import AuthConfig

class AnthropicLLMClient:
    """Production LLM client using Anthropic API or Vertex AI."""

    def __init__(self, auth_config: AuthConfig):
        self.auth_config = auth_config
        self.client = self._create_client()

    def _create_client(self) -> Anthropic | AnthropicVertex:
        """Create appropriate client based on auth method."""
        if self.auth_config.auth_method == "vertex_ai":
            return AnthropicVertex(
                project_id=self.auth_config.vertex_project_id,
                region=self.auth_config.vertex_region,
                credentials_file=self.auth_config.vertex_credentials_file,
            )
        elif self.auth_config.auth_method == "api_key":
            return Anthropic(api_key=self.auth_config.api_key)
        else:
            raise ValueError(f"Unknown auth method: {self.auth_config.auth_method}")

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Send query to Anthropic API."""
        try:
            response = await self.client.messages.create(
                model=request.model,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.user_prompt}],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                finish_reason=FinishReason(response.stop_reason),
            )

        except anthropic.RateLimitError as e:
            retry_after = int(e.response.headers.get("retry-after", 60))
            raise RateLimitError(retry_after_seconds=retry_after) from e

        except anthropic.BadRequestError as e:
            if "context length" in str(e).lower():
                raise ContextLengthExceeded(
                    tokens_sent=estimate_tokens(request),
                    max_tokens=200_000,
                ) from e
            raise InvalidRequestError(str(e)) from e

        except anthropic.AuthenticationError as e:
            raise AuthenticationError(str(e)) from e

    async def query_structured(
        self,
        request: LLMRequest,
        schema: type[BaseModel],
    ) -> tuple[BaseModel, LLMResponse]:
        """Query with structured output parsing."""
        # Add JSON schema instruction to system prompt
        enhanced_request = LLMRequest(
            system_prompt=request.system_prompt + f"\n\nReturn response as JSON matching: {schema.model_json_schema()}",
            user_prompt=request.user_prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        response = await self.query(enhanced_request)

        # Parse JSON response
        try:
            parsed = schema.model_validate_json(response.content)
            return parsed, response
        except ValidationError as e:
            raise ValidationError(f"Failed to parse LLM response: {e}") from e
```

### Test Implementation

```python
class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses: dict[str, str] | None = None):
        """
        Args:
            responses: Map from user prompt prefix to canned response.
                      If None, returns empty responses.
        """
        self.responses = responses or {}
        self.queries: list[LLMRequest] = []  # Track queries for assertions

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Return canned response based on user prompt."""
        self.queries.append(request)

        # Find matching response
        for prefix, content in self.responses.items():
            if request.user_prompt.startswith(prefix):
                return LLMResponse(
                    content=content,
                    model=request.model,
                    input_tokens=len(request.system_prompt + request.user_prompt) // 4,
                    output_tokens=len(content) // 4,
                    finish_reason=FinishReason.STOP,
                )

        # Default response
        return LLMResponse(
            content='{"entities": []}',
            model=request.model,
            input_tokens=100,
            output_tokens=10,
            finish_reason=FinishReason.STOP,
        )

    async def query_structured(
        self,
        request: LLMRequest,
        schema: type[BaseModel],
    ) -> tuple[BaseModel, LLMResponse]:
        """Return structured response."""
        response = await self.query(request)
        parsed = schema.model_validate_json(response.content)
        return parsed, response

    def assert_query_count(self, expected: int) -> None:
        """Assert number of queries made."""
        assert len(self.queries) == expected, \
            f"Expected {expected} queries, got {len(self.queries)}"

    def assert_query_contains(self, text: str) -> None:
        """Assert at least one query contained text."""
        assert any(text in q.user_prompt or text in q.system_prompt for q in self.queries), \
            f"No query contained '{text}'"
```

### Retry Decorator

```python
import asyncio
from functools import wraps

class RetryingLLMClient:
    """
    Decorator that adds retry logic with exponential backoff.

    Wraps any LLMClient implementation to add resilience.
    """

    def __init__(
        self,
        inner: LLMClient,
        max_retries: int = 3,
        initial_backoff_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
    ):
        self.inner = inner
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff_seconds
        self.multiplier = backoff_multiplier

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Query with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await self.inner.query(request)

            except RateLimitError as e:
                last_exception = e
                backoff = e.retry_after_seconds or (
                    self.initial_backoff * (self.multiplier ** attempt)
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(backoff)
                continue

            except (ContextLengthExceeded, AuthenticationError, InvalidRequestError):
                # Don't retry these - they won't succeed
                raise

            except LLMError as e:
                # Retry other errors
                last_exception = e
                if attempt < self.max_retries - 1:
                    backoff = self.initial_backoff * (self.multiplier ** attempt)
                    await asyncio.sleep(backoff)
                continue

        raise MaxRetriesExceeded(
            f"Failed after {self.max_retries} retries"
        ) from last_exception

    async def query_structured(
        self,
        request: LLMRequest,
        schema: type[BaseModel],
    ) -> tuple[BaseModel, LLMResponse]:
        """Query structured with retry logic."""
        # Retry logic is applied at query() level
        return await self.inner.query_structured(request, schema)

class MaxRetriesExceeded(LLMError):
    """All retries exhausted."""
    pass
```

### Cost Tracking Decorator

```python
from dataclasses import dataclass

@dataclass
class CostMetrics:
    """Accumulated cost metrics."""
    total_queries: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_errors: int = 0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def estimate_cost_usd(
        self,
        input_cost_per_mtok: float = 3.0,  # $3/MTok for Sonnet
        output_cost_per_mtok: float = 15.0,  # $15/MTok for Sonnet
    ) -> float:
        """Estimate total cost in USD."""
        input_cost = (self.total_input_tokens / 1_000_000) * input_cost_per_mtok
        output_cost = (self.total_output_tokens / 1_000_000) * output_cost_per_mtok
        return input_cost + output_cost

class CostTrackingLLMClient:
    """Decorator that tracks token usage and cost."""

    def __init__(self, inner: LLMClient):
        self.inner = inner
        self.metrics = CostMetrics()

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Query and track cost."""
        try:
            response = await self.inner.query(request)
            self.metrics.total_queries += 1
            self.metrics.total_input_tokens += response.input_tokens
            self.metrics.total_output_tokens += response.output_tokens
            return response

        except LLMError:
            self.metrics.total_errors += 1
            raise

    async def query_structured(
        self,
        request: LLMRequest,
        schema: type[BaseModel],
    ) -> tuple[BaseModel, LLMResponse]:
        """Query structured and track cost."""
        parsed, response = await self.inner.query_structured(request, schema)
        self.metrics.total_queries += 1
        self.metrics.total_input_tokens += response.input_tokens
        self.metrics.total_output_tokens += response.output_tokens
        return parsed, response

    def get_metrics(self) -> CostMetrics:
        """Get current metrics."""
        return self.metrics

    def reset_metrics(self) -> None:
        """Reset metrics to zero."""
        self.metrics = CostMetrics()
```

## Usage Examples

### Basic Usage (Production)

```python
from kg_extractor.llm import AnthropicLLMClient, LLMRequest
from kg_extractor.config import AuthConfig

# Create client
auth = AuthConfig(auth_method="vertex_ai", vertex_project_id="my-project")
client = AnthropicLLMClient(auth)

# Send query
request = LLMRequest(
    system_prompt="You are a helpful assistant.",
    user_prompt="What is 2+2?",
)
response = await client.query(request)

print(response.content)  # "4"
print(f"Tokens used: {response.total_tokens}")
```

### With Retry and Cost Tracking

```python
# Compose decorators
base_client = AnthropicLLMClient(auth)
retrying_client = RetryingLLMClient(base_client, max_retries=3)
client = CostTrackingLLMClient(retrying_client)

# Use as normal
response = await client.query(request)

# Check metrics
metrics = client.get_metrics()
print(f"Total cost: ${metrics.estimate_cost_usd():.2f}")
print(f"Error rate: {metrics.total_errors / metrics.total_queries:.2%}")
```

### Testing with Mocks

```python
# tests/test_extraction.py
async def test_extraction_agent():
    # Arrange: Create mock client
    mock_client = MockLLMClient(responses={
        "Extract entities": '{"entities": [{"@id": "urn:service:foo", "@type": "Service", "name": "Foo"}]}',
    })

    agent = ExtractionAgent(llm_client=mock_client, ...)

    # Act
    result = await agent.extract(files=[...])

    # Assert
    mock_client.assert_query_count(1)
    mock_client.assert_query_contains("Extract entities")
    assert result.entity_count == 1
```

### Structured Output

```python
from pydantic import BaseModel

class ExtractionResult(BaseModel):
    entities: list[dict]
    metadata: dict

request = LLMRequest(
    system_prompt="Extract entities from data.",
    user_prompt="...",
)

result, response = await client.query_structured(request, ExtractionResult)

# result is typed as ExtractionResult
for entity in result.entities:
    print(entity["name"])
```

## Design Rationale

### Why Protocol Instead of ABC?

**Protocol** (structural subtyping) allows:

- Duck typing: Any class with matching methods satisfies protocol
- No inheritance required
- Better for testing (don't need to subclass)

### Why Immutable Dataclasses?

**Immutability** ensures:

- Thread safety (can share across async tasks)
- Hashable (can use as dict keys, cache keys)
- Prevents accidental mutation
- Clear data flow

### Why Separate Request/Response?

**Separation** enables:

- Clear contract between caller and LLM
- Easy to log/cache requests
- Response can be serialized for metrics
- Testing: create responses without calling LLM

### Why Decorator Pattern?

**Decorators** (composition over inheritance) allow:

- Mix and match concerns (retry + cost tracking)
- Add features without modifying core client
- Test decorators independently
- Runtime composition

## Testing Contract

All implementations of `LLMClient` MUST pass this test suite:

```python
# tests/contracts/test_llm_client_contract.py
import pytest
from typing import Type

@pytest.mark.parametrize("client_class", [
    AnthropicLLMClient,
    MockLLMClient,
    RetryingLLMClient,
    CostTrackingLLMClient,
])
async def test_llm_client_contract(client_class: Type[LLMClient]):
    """All LLMClient implementations must satisfy this contract."""
    client = create_client(client_class)  # Factory function

    request = LLMRequest(
        system_prompt="Test",
        user_prompt="Hello",
    )

    response = await client.query(request)

    # Contract assertions
    assert isinstance(response, LLMResponse)
    assert isinstance(response.content, str)
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert isinstance(response.finish_reason, FinishReason)
```

## Migration Path

**Phase 1 (Skateboard)**: Basic interface

- AnthropicLLMClient (production)
- MockLLMClient (testing)

**Phase 2 (Scooter)**: Add resilience

- RetryingLLMClient decorator
- CostTrackingLLMClient decorator

**Phase 3 (Bicycle)**: Add optimizations

- CachingLLMClient decorator (cache responses by request hash)
- RateLimitingLLMClient decorator (throttle requests)

**Phase 4 (Car)**: Advanced features

- BatchingLLMClient (batch multiple requests)
- CircuitBreakerLLMClient (fail fast when errors spike)

## References

- [Protocol Pattern (PEP 544)](https://peps.python.org/pep-0544/)
- [Decorator Pattern](https://refactoring.guru/design-patterns/decorator)
- [Anthropic API Documentation](https://docs.anthropic.com/en/api)
