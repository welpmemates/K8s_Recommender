"""
yaml_generator.py — Phase 8: YAML Persistence + Change Detection

WHAT CHANGED FROM PHASE 7:
  Phase 7 = print only (every tick)
  Phase 8 adds:
    1. Change detection  — only act when values shift > 10%
    2. File persistence  — write to generated_resources.yaml
    3. Return values     — expose cpu_requests_m + memory_requests_mi
                          so main.py can push them to Prometheus

WHY CHANGE DETECTION:
  Without it, we'd rewrite the YAML file every 15 seconds.
  In Phase 9+ when we apply this to the cluster, that would
  trigger continuous rolling restarts — catastrophic.
  10% threshold = absorbs normal metric jitter, reacts to
  genuine workload shifts.

WHY RETURN THE MILLICORES / MI VALUES:
  main.py needs them to set recommended_cpu_millicores and
  recommended_memory_megabytes Prometheus gauges so Grafana
  can plot Actual vs Predicted vs Safe vs Recommended all
  on one panel.
"""

import math
import os

# PyYAML — already available in Python stdlib alternative is
# manual string formatting but yaml.dump gives cleaner output
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("⚠️  PyYAML not installed — will use manual YAML formatting")


# -------------------------------
# TUNABLE CONSTANTS
# -------------------------------

SAFETY_BUFFER     = 1.2   # 20% headroom on top of safe values
LIMITS_MULTIPLIER = 2.0   # limits = 2x requests

# Change detection threshold: only update if values drift > 10%
CHANGE_THRESHOLD = 0.10

# Output file path — writes to the hostPath volume mounted from:
#   host:      ~/Documents/K8s_Recommender/infra/aggregator/generation/
#   minikube:  /mnt/aggregator-output/
#   container: /mnt/aggregator-output/
# All three point to the same directory via `minikube mount`.
OUTPUT_FILE = "/mnt/aggregator-output/generated_resources.yaml"


# -------------------------------
# MODULE-LEVEL STATE
# (tracks last written values for change detection)
#
# WHY module-level and not class:
#   yaml_generator is called as a standalone function from main.py.
#   Keeping state here avoids having to thread an object through
#   the entire Aggregator class just for this purpose.
# -------------------------------

_last_cpu_m  = None   # last written cpu_requests_m  (millicores)
_last_mem_mi = None   # last written memory_requests_mi (MiB)


# -------------------------------
# UNIT CONVERSION HELPERS
# -------------------------------

def cores_to_millicores(cores: float) -> int:
    """
    Fractional CPU cores → millicores (K8s unit).
    Always ceil — rounding down under-provisions.
    Floor at 1m to avoid a 0m spec.
    """
    return max(math.ceil(cores * 1000), 1)


def bytes_to_mebibytes(byte_value: float) -> int:
    """
    Bytes → Mebibytes (MiB) — K8s binary memory unit.
    Always ceil — rounding down under-provisions.
    Floor at 1Mi to avoid a 0Mi spec.
    """
    return max(math.ceil(byte_value / (1024 ** 2)), 1)


# -------------------------------
# CHANGE DETECTION
# -------------------------------

def _has_changed(new_val: float, old_val: float,
                 threshold: float = CHANGE_THRESHOLD) -> bool:
    """
    Return True if the relative change exceeds threshold.

    WHY relative (not absolute):
      Absolute deltas mean different things at different scales.
      e.g. 5m CPU change is huge at 10m baseline, tiny at 2000m.
      Relative change is scale-invariant.

    Edge case — old_val is None (first run):
      Always write on first run so the file exists immediately.
    """
    if old_val is None:
        return True
    if old_val == 0:
        return new_val != 0
    return abs(new_val - old_val) / old_val > threshold


# -------------------------------
# YAML FILE WRITER
# -------------------------------

def _write_yaml_file(resource_spec: dict):
    """
    Write resource spec to generated_resources.yaml.

    WHY overwrite vs append:
      This file represents the CURRENT recommendation, not a log.
      The latest value is all that matters for cluster application.

    Format written (manual fallback if PyYAML missing):

      resources:
        requests:
          cpu: 250m
          memory: 300Mi
        limits:
          cpu: 500m
          memory: 600Mi
    """
    try:
        with open(OUTPUT_FILE, "w") as f:
            if YAML_AVAILABLE:
                yaml.dump(resource_spec, f, default_flow_style=False)
            else:
                # Manual YAML formatting — valid K8s YAML
                r = resource_spec["resources"]
                f.write("resources:\n")
                f.write("  requests:\n")
                f.write(f"    cpu: {r['requests']['cpu']}\n")
                f.write(f"    memory: {r['requests']['memory']}\n")
                f.write("  limits:\n")
                f.write(f"    cpu: {r['limits']['cpu']}\n")
                f.write(f"    memory: {r['limits']['memory']}\n")

        print(f"✅ YAML written to: {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ Failed to write YAML file: {e}")


# -------------------------------
# PRETTY PRINTER
# -------------------------------

def _print_yaml(spec: dict, raw_cpu: float, raw_memory: float,
                buffered_cpu: float, buffered_memory: float):
    """
    Print the full resource spec with input context.
    Kept from Phase 7 — useful for log tracing.
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


# -------------------------------
# CORE GENERATOR (PUBLIC API)
# -------------------------------

def generate_resources_yaml(safe_cpu: float, safe_memory: float) -> dict:
    """
    Convert safe predictions → K8s resource spec.

    Args:
        safe_cpu    (float): Safety-adjusted CPU in cores
        safe_memory (float): Safety-adjusted memory in bytes

    Returns:
        dict with keys:
            "resources"          → full K8s resource spec
            "cpu_requests_m"     → int, millicores (for Prometheus)
            "memory_requests_mi" → int, MiB        (for Prometheus)

    Flow:
        safe value
          → 20% buffer
          → convert to K8s units
          → change detection (compare to last written values)
          → if changed: print + write file
          → if unchanged: skip (log only)
          → always return values for Prometheus gauges
    """
    global _last_cpu_m, _last_mem_mi

    # Step 1: Apply safety buffer
    cpu_buffered    = safe_cpu    * SAFETY_BUFFER
    memory_buffered = safe_memory * SAFETY_BUFFER

    # Step 2: Convert to K8s units
    cpu_requests_m     = cores_to_millicores(cpu_buffered)
    memory_requests_mi = bytes_to_mebibytes(memory_buffered)

    # Step 3: Compute limits (2x requests)
    cpu_limits_m      = math.ceil(cpu_requests_m     * LIMITS_MULTIPLIER)
    memory_limits_mi  = math.ceil(memory_requests_mi * LIMITS_MULTIPLIER)

    # Step 4: Build resource spec dict
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

    # Step 5: Change detection
    cpu_changed = _has_changed(cpu_requests_m,     _last_cpu_m)
    mem_changed = _has_changed(memory_requests_mi, _last_mem_mi)

    if cpu_changed or mem_changed:
        # Print full spec to logs
        _print_yaml(resource_spec, safe_cpu, safe_memory,
                    cpu_buffered, memory_buffered)

        # Persist to file
        _write_yaml_file(resource_spec)

        # Update tracked state
        _last_cpu_m  = cpu_requests_m
        _last_mem_mi = memory_requests_mi

    else:
        # Minimal log — don't spam every 15s
        print(f"⏸️  No significant change — skipping YAML update "
              f"(cpu={cpu_requests_m}m mem={memory_requests_mi}Mi)")

    # Step 6: Always return values so main.py can set Prometheus gauges
    return {
        "resource_spec":      resource_spec,
        "cpu_requests_m":     cpu_requests_m,
        "memory_requests_mi": memory_requests_mi
    }
