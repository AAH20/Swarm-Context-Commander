variable "namespace" {
  type        = string
  description = "Dedicated namespace for an operator-managed Swarm-Context-Commander installation."
  default     = "swarm-context-commander"

  validation {
    condition     = can(regex("^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", var.namespace))
    error_message = "namespace must be a Kubernetes DNS label"
  }
}

variable "max_active_tasks" {
  type        = number
  description = "Initial global admission cap. This module does not run a scheduler."
  default     = 100

  validation {
    condition     = var.max_active_tasks >= 1 && var.max_active_tasks <= 100000
    error_message = "max_active_tasks must be between 1 and 100000"
  }
}

variable "max_context_tokens" {
  type        = number
  description = "Initial per-task context token budget."
  default     = 4096

  validation {
    condition     = var.max_context_tokens >= 256 && var.max_context_tokens <= 32768
    error_message = "max_context_tokens must be between 256 and 32768"
  }
}
