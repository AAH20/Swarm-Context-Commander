# This conservative module creates configuration only. It does not provision
# cluster nodes, GPUs, queues, vLLM, or computer-use executors.
resource "kubernetes_namespace_v1" "commander" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/name"       = "swarm-context-commander"
      "app.kubernetes.io/part-of"    = "agent-infrastructure"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

resource "kubernetes_config_map_v1" "admission" {
  metadata {
    name      = "swarm-context-commander-admission"
    namespace = kubernetes_namespace_v1.commander.metadata[0].name
  }
  data = {
    MAX_ACTIVE_TASKS  = tostring(var.max_active_tasks)
    MAX_CONTEXT_TOKENS = tostring(var.max_context_tokens)
  }
}
