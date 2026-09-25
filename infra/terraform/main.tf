# This conservative module creates configuration only. It does not provision
# cluster nodes, GPUs, queues, vLLM, or computer-use executors.
resource "kubernetes_namespace_v1" "swarmcontext" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/name"       = "swarmcontext-plane"
      "app.kubernetes.io/part-of"    = "agent-infrastructure"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

resource "kubernetes_config_map_v1" "admission" {
  metadata {
    name      = "swarmcontext-admission"
    namespace = kubernetes_namespace_v1.swarmcontext.metadata[0].name
  }
  data = {
    MAX_ACTIVE_TASKS  = tostring(var.max_active_tasks)
    MAX_CONTEXT_TOKENS = tostring(var.max_context_tokens)
  }
}
