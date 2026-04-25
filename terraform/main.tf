terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "sessioncast-tfstate"
    prefix = "terraform/state"
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-northeast1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "aiplatform.googleapis.com",
    "pubsub.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudfunctions.googleapis.com",
    "secretmanager.googleapis.com",
    "firebase.googleapis.com",
    "firestore.googleapis.com",
    "identitytoolkit.googleapis.com",
    "cloudtrace.googleapis.com",
    "monitoring.googleapis.com",
    "bigquery.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "sessioncast" {
  location      = var.region
  repository_id = "sessioncast"
  format        = "DOCKER"
  description   = "SessionCast container images"
}

# GCS bucket for generated media assets
resource "google_storage_bucket" "media" {
  name          = "${var.project_id}-sessioncast-media"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition { age = 365 }
    action    { type = "SetStorageClass"; storage_class = "NEARLINE" }
  }
}

# Pub/Sub topic for pipeline events
resource "google_pubsub_topic" "pipeline_events" {
  name = "sessioncast-pipeline-events"
}

# BigQuery dataset for observability
resource "google_bigquery_dataset" "observability" {
  dataset_id    = "sessioncast_observability"
  friendly_name = "SessionCast Observability"
  location      = var.region
}

resource "google_bigquery_table" "pipeline_accuracy" {
  dataset_id = google_bigquery_dataset.observability.dataset_id
  table_id   = "pipeline_accuracy"
  deletion_protection = false

  schema = jsonencode([
    { name = "episode_id", type = "STRING", mode = "REQUIRED" },
    { name = "step_name",  type = "STRING", mode = "REQUIRED" },
    { name = "score",      type = "FLOAT",  mode = "REQUIRED" },
    { name = "created_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}
