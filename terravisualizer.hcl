# Terravisualizer Configuration Example
# This file defines how resources should be grouped in the visualization

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

"aws_instance" {
    "grouped_by" = [values.availability_zone]
    "diagramm_image" = "../icons/aws_instance"
    "name" = "values.tags.Name"
}

"aws_s3_bucket" {
    "grouped_by" = [values.region]
    "diagramm_image" = "../icons/aws_s3_bucket"
    "name" = "values.bucket"
}
