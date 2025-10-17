<template>
  <div class="bg-card border border-border rounded-lg">
    <!-- Header -->
    <div class="p-6 border-b border-border">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-foreground">Usage Overview</h2>
          <p class="text-sm text-muted-foreground mt-1">
            Platform usage over time
          </p>
        </div>
        <div class="flex items-center gap-3">
          <!-- Time range selector -->
          <select
            v-model="timeRange"
            @change="fetchUsageStats"
            class="px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option :value="7">Last 7 days</option>
            <option :value="30">Last 30 days</option>
            <option :value="90">Last 90 days</option>
          </select>

          <button
            @click="fetchUsageStats"
            class="px-4 py-2 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="p-6">
      <div class="space-y-6">
        <div class="h-64 bg-muted rounded animate-pulse"></div>
        <div class="h-64 bg-muted rounded animate-pulse"></div>
      </div>
    </div>

    <!-- Charts -->
    <div v-else class="p-6 space-y-8">
      <!-- Web Usage Chart -->
      <div>
        <h3 class="text-sm font-semibold text-foreground mb-4">
          Web Usage (Conversations & Messages)
        </h3>
        <div class="bg-card rounded-lg border border-border p-4">
          <Line
            :data="webChartData"
            :options="webChartOptions"
            :height="150"
          />
        </div>
      </div>

      <!-- API Usage Chart -->
      <div>
        <h3 class="text-sm font-semibold text-foreground mb-4">
          API Usage (MCP Queries)
        </h3>
        <div class="bg-card rounded-lg border border-border p-4">
          <Line
            :data="apiChartData"
            :options="apiChartOptions"
            :height="150"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  type ChartOptions,
} from "chart.js";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

interface UsageStats {
  timeRange: number;
  granularity: string;
  labels: string[];
  webUsage: {
    conversations: number[];
    messages: number[];
  };
  apiUsage: {
    queries: number[];
  };
}

const loading = ref(false);
const timeRange = ref(30);
const usageStats = ref<UsageStats | null>(null);

// Fetch usage stats from API
async function fetchUsageStats() {
  loading.value = true;
  try {
    usageStats.value = await $fetch("/api/admin/usage-stats", {
      query: {
        timeRange: timeRange.value,
        granularity: "daily",
      },
    });
  } catch (error) {
    console.error("Failed to fetch usage stats:", error);
  } finally {
    loading.value = false;
  }
}

// Format labels for display
const formattedLabels = computed(() => {
  if (!usageStats.value) return [];

  return usageStats.value.labels.map((label) => {
    const date = new Date(label);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  });
});

// Web usage chart data
const webChartData = computed(() => ({
  labels: formattedLabels.value,
  datasets: [
    {
      label: "Conversations",
      data: usageStats.value?.webUsage.conversations || [],
      borderColor: "rgb(59, 130, 246)",
      backgroundColor: "rgba(59, 130, 246, 0.1)",
      fill: true,
      tension: 0.4,
    },
    {
      label: "Messages",
      data: usageStats.value?.webUsage.messages || [],
      borderColor: "rgb(147, 51, 234)",
      backgroundColor: "rgba(147, 51, 234, 0.1)",
      fill: true,
      tension: 0.4,
    },
  ],
}));

// API usage chart data
const apiChartData = computed(() => ({
  labels: formattedLabels.value,
  datasets: [
    {
      label: "API Queries",
      data: usageStats.value?.apiUsage.queries || [],
      borderColor: "rgb(16, 185, 129)",
      backgroundColor: "rgba(16, 185, 129, 0.1)",
      fill: true,
      tension: 0.4,
    },
  ],
}));

// Chart options for web usage
const webChartOptions: ChartOptions<"line"> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: "top",
      align: "end",
      labels: {
        usePointStyle: true,
        pointStyle: "circle",
        padding: 20,
        font: {
          size: 13,
          family: "inherit",
        },
        color: "#64748b",
      },
    },
    tooltip: {
      mode: "index",
      intersect: false,
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      padding: 12,
      cornerRadius: 8,
      titleFont: {
        size: 13,
        weight: "bold",
      },
      bodyFont: {
        size: 12,
      },
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        precision: 0,
        color: "#94a3b8",
        font: {
          size: 11,
        },
      },
      grid: {
        color: "rgba(148, 163, 184, 0.1)",
      },
    },
    x: {
      ticks: {
        color: "#94a3b8",
        font: {
          size: 11,
        },
        maxRotation: 45,
        minRotation: 0,
      },
      grid: {
        display: false,
      },
    },
  },
};

// Chart options for API usage
const apiChartOptions: ChartOptions<"line"> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: "top",
      align: "end",
      labels: {
        usePointStyle: true,
        pointStyle: "circle",
        padding: 20,
        font: {
          size: 13,
          family: "inherit",
        },
        color: "#64748b",
      },
    },
    tooltip: {
      mode: "index",
      intersect: false,
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      padding: 12,
      cornerRadius: 8,
      titleFont: {
        size: 13,
        weight: "bold",
      },
      bodyFont: {
        size: 12,
      },
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        precision: 0,
        color: "#94a3b8",
        font: {
          size: 11,
        },
      },
      grid: {
        color: "rgba(148, 163, 184, 0.1)",
      },
    },
    x: {
      ticks: {
        color: "#94a3b8",
        font: {
          size: 11,
        },
        maxRotation: 45,
        minRotation: 0,
      },
      grid: {
        display: false,
      },
    },
  },
};

// Load data on mount
onMounted(() => {
  fetchUsageStats();
});
</script>
