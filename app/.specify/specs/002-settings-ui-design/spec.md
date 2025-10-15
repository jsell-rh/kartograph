# Settings UI Implementation Plan

## Design Principles

**Enterprise-Ready UX Requirements**:

1. Clear Information Hierarchy
2. Progressive Disclosure
3. Confirmation Patterns for critical actions
4. Visual Feedback (loading, success, error)
5. Security Best Practices (show token once, confirm destructive actions)
6. Accessibility (ARIA, keyboard nav, screen reader)
7. Responsive Design

## Navigation Flow

```
Header (User Menu) → Settings Menu Item → Settings Page (/settings)
                                              ↓
                                         API Tokens Tab
```

## Component Structure

```
pages/
  settings/
    index.vue          ← Main settings page with tabs

components/
  settings/
    TokenList.vue           ← List of tokens with cards
    TokenCard.vue           ← Individual token display
    CreateTokenModal.vue    ← Create token wizard
    TokenCreatedModal.vue   ← Show-once token display
    RevokeTokenModal.vue    ← Revoke confirmation

composables/
  useTokens.ts         ← State management for tokens
```

## Features

### 1. Token List View

- Card-based layout
- Shows: name, created date, last used, query count, expiry
- Status indicators (active, expired, never used)
- Actions: Revoke button

### 2. Create Token Modal

- Input: Token name (required)
- Dropdown: Expiry (30/90/180/365 days)
- Validation: Name required, max length
- Submit → API call → Success modal

### 3. Token Created Success Modal

- **Show token ONCE** with warning
- Copy button for token
- Copy button for full Claude Desktop JSON config
- Must acknowledge before closing

### 4. Revoke Token Confirmation

- Show token name
- Warn about immediate invalidation
- Confirm/Cancel buttons
- On confirm → API call → Remove from list

## Visual Design

**Colors** (existing palette):

- Background: `bg-background`
- Cards: `bg-card/80 backdrop-blur-md`
- Borders: `border-border/40`
- Primary: `bg-primary`
- Destructive: `bg-destructive`

**Status Indicators**:

- Active: Green dot
- Expired: Red dot
- Never Used: Gray dot

**Micro-interactions**:

- Hover states
- Smooth transitions
- Copy feedback ("Copied!")
- Loading spinners
- Toast notifications

## Implementation Steps

1. Create settings page with navigation
2. Build token list with empty state
3. Implement token cards
4. Create token creation modal
5. Build token success modal with copy
6. Add revoke confirmation modal
7. Wire up API calls
8. Add toast notifications
9. Test all flows
10. Polish animations

## API Integration

- GET /api/tokens → Fetch token list
- POST /api/tokens → Create token
- DELETE /api/tokens/:id → Revoke token

## Accessibility

- ARIA labels
- Focus management
- Keyboard shortcuts (ESC)
- Screen reader announcements
- WCAG AA contrast

## Mobile Responsive

- Stack layout on mobile
- Full-width cards
- Touch-friendly buttons (44x44px)
- Full-screen modals
