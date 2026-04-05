"""
yaml_generator.py — Phase 7: YAML Generator

WHY THIS EXISTS:
  The safety guard gives us safe_cpu and safe_memory values.
  But Kubernetes doesn't read floats — it reads resource specs
  in its own format (millicores for CPU, Mi for memory).

  This module:
    1. Converts raw values into K8s units
    2. Applies a 20% safety buffer on top of p95-safe values
    3. Sets limits = 2x requests (standard K8s pattern)
    4. Prints the final YAML block to stdout

  Phase 7 = GENERATION ONLY.
  We do NOT apply this to the cluster yet (that's Phase 8+).
"""

import math
# -------------------------------
# TUNABLE CONSTANTS
#
# WHY 1.2 buffer:
#   p95 captures 95% of observed load but spikes can exceed it.
#   A 20% headroom absorbs short bursts without OOMKill.
#   In production this would be configurable per-service SLA.
#
# WHY limits = 2x requests:
#   K8s requests = what the scheduler guarantees.
#   K8s limits   = hard ceiling before throttle/OOMKill.
#   2x is the industry-standard starting ratio for
#   bursty workloads. Too tight → OOMKill. Too loose → waste.
# -------------------------------

SAFETY_BUFFER    = 1.2   # 20% headroom on top of safe values
LIMITS_MULTIPLIER = 2.0  # limits = 2x requests


# -------------------------------
# UNIT CONVERSION HELPERS
# -------------------------------

def cores_to_millicores(cores: float) -> int:
    """
    Convert fractional CPU cores → millicores (K8s unit).

    WHY ceil:
      We always round UP for resource allocation.
      Rounding down would give K8s less than needed.

    Examples:
      0.2  cores → 200m
      0.05 cores →  50m
      0.001 cores → 1m  (minimum meaningful value)
    """
    millicores = math.ceil(cores * 1000)
    return max(millicores, 1)  # floor at 1m to avoid 0m spec


def bytes_to_mebibytes(byte_value: float) -> int:
    """
    Convert bytes → Mebibytes (MiB) — K8s memory unit.

    WHY ceil:
      Same reason as CPU — always round up for safety.

    WHY MiB not MB:
      Kubernetes uses binary units (1 Mi = 1024^2 bytes).
      Using MB (1000^2) would silently underprovision.

    Examples:
      52428800  bytes →  50 Mi
      104857600 bytes → 100 Mi
    """
    mib = math.ceil(byte_value / (1024 ** 2))
    return max(mib, 1)  # floor at 1Mi to avoid 0Mi spec


# -------------------------------
# CORE GENERATOR
# -------------------------------

def generate_resources_yaml(safe_cpu: float, safe_memory: float) -> dict:
    """
    Convert safe predictions → K8s resource spec dict + print YAML.

    Args:
        safe_cpu    (float): Safety-adjusted CPU in cores (e.g. 0.18)
        safe_memory (float): Safety-adjusted memory in bytes (e.g. 55050240)

    Returns:
        dict: resource spec with requests + limits

    Flow:
        safe value
            → apply 20% buffer       (absorb spikes)
            → convert to K8s units   (millicores / Mi)
            → set requests
            → limits = 2x requests
    """

    # Step 1: Apply safety buffer
    cpu_buffered    = safe_cpu    * SAFETY_BUFFER
    memory_buffered = safe_memory * SAFETY_BUFFER

    # Step 2: Convert to K8s units
    cpu_requests_m    = cores_to_millicores(cpu_buffered)
    memory_requests_mi = bytes_to_mebibytes(memory_buffered)

    # Step 3: Compute limits (2x requests)
    cpu_limits_m      = math.ceil(cpu_requests_m    * LIMITS_MULTIPLIER)
    memory_limits_mi  = math.ceil(memory_requests_mi * LIMITS_MULTIPLIER)

    # Step 4: Build resource dict
    resource_spec = {
        "resources": {
            "requests": {
                "cpu":    f"{cpu_requests_m}m",
                "memory": f"{memory_requests_mi}Mi"
            },
            "limits": {
                "cpu":    f"{cpu_limits_m}m",
                "memory": f"{memory_limits_mi}Mi"
            }
        }
    }

    # Step 5: Print formatted YAML block
    _print_yaml(resource_spec, safe_cpu, safe_memory,
                cpu_buffered, memory_buffered)

    return resource_spec


def _print_yaml(spec: dict, raw_cpu: float, raw_memory: float,
                buffered_cpu: float, buffered_memory: float):
    """
    Pretty-print the generated resource spec with context.

    WHY print raw + buffered values:
      Makes it easy to see how much the buffer added.
      Critical for tuning SAFETY_BUFFER in production.
    """
    requests = spec["resources"]["requests"]
    limits   = spec["resources"]["limits"]

    print("\n" + "=" * 50)
    print("📦 GENERATED KUBERNETES RESOURCES")
    print("=" * 50)

    print(f"\n  Input (safe values from p95 guard):")
    print(f"    cpu_safe    : {raw_cpu:.6f} cores")
    print(f"    memory_safe : {raw_memory / (1024**2):.2f} Mi  ({int(raw_memory)} bytes)")

    print(f"\n  After {int((SAFETY_BUFFER - 1) * 100)}% safety buffer:")
    print(f"    cpu_buffered    : {buffered_cpu:.6f} cores")
    print(f"    memory_buffered : {buffered_memory / (1024**2):.2f} Mi")

    print(f"\n  resources:")
    print(f"    requests:")
    print(f"      cpu:    {requests['cpu']}")
    print(f"      memory: {requests['memory']}")
    print(f"    limits:")
    print(f"      cpu:    {limits['cpu']}")
    print(f"      memory: {limits['memory']}")

    print("\n" + "=" * 50 + "\n")
