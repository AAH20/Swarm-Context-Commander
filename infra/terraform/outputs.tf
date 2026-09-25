output "namespace" {
  description = "Namespace created for a separately deployed runtime."
  value       = kubernetes_namespace_v1.commander.metadata[0].name
}

output "admission_config_map" {
  description = "Name of the bounded admission configuration."
  value       = kubernetes_config_map_v1.admission.metadata[0].name
}
