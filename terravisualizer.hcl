# Terravisualizer Configuration Example
# This file defines how resources should be grouped in the visualization

"google_compute_address" {
    "grouped_by" = [values.project, values.region]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.name}"
}

"google_storage_bucket" {
    "grouped_by" = [values.project, values.location]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.name}"
}

"google_compute_firewall" {
    "grouped_by" = [values.project]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.name}"
}

"google_compute_region_ssl_policy" {
    "grouped_by" = [values.project, values.region]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.name}"
}

"google_compute_reservation" {
    "grouped_by" = [values.project]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.name}"
}

"google_compute_reservation" {
    "grouped_by" = [values.project]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.name}"
}

"google_container_cluster" {
    "grouped_by" = [values.project, values.location]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.name}"
    "id"   = "values.id"
}

"google_container_node_pool" {
    "group_id" = "values.cluster"
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.name}"
}

"google_dns_record_set" {
    "grouped_by" = [values.project, values.managed_zone]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.name}"
}

"google_iap_web_region_backend_service_iam_member" {
    "grouped_by" = [values.project, values.web_region_backend_service]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.member}-${values.role}"
}

"google_project_iam_member" {
    "grouped_by" = [values.project]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.member}-${values.role}"
}

"google_secret_manager_secret" {
    "grouped_by" = [values.project]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.secret_id}"
}

"google_service_account" {
    "grouped_by" = [values.project]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.display_name}"
    "id" = "values.id"
}

"google_service_account_iam_member" {
    "group_id" = "values.service_account_id"
    "grouped_by" = [values.member]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "${values.role}"
}
