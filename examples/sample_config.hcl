# Example Configuration for Terravisualizer

"google_compute_address" {
    "grouped_by" = [values.project, values.region]
    "diagramm_image" = "../icons/google_compute_address"
    "name" = "values.name"
}

"google_compute_instance" {
    "grouped_by" = [values.project, values.zone]
    "diagramm_image" = "../icons/google_compute_instance"
    "name" = "values.name"
}
