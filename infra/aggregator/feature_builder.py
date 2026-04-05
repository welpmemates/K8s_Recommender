import time


class FeatureBuilder:
    def __init__(self):
        pass

    def compute_demand(self, request_rate):
        """
        Estimate resource demand from request rate

        Assumption:
        Each request contributes some avg CPU & memory cost
        """

        # Tunable constants (IMPORTANT)
        CPU_PER_REQUEST = 0.005      # cores
        MEM_PER_REQUEST = 5 * 1024 * 1024  # 5 MB in bytes

        cpu_demand = request_rate * CPU_PER_REQUEST
        memory_demand = request_rate * MEM_PER_REQUEST

        return cpu_demand, memory_demand

    def compute_heavy_ratio(self, request_rate):
        """
        Placeholder for heavy request ratio

        Since we don't yet classify requests,
        we simulate:
        - low traffic → mostly light
        - high traffic → more heavy
        """

        if request_rate < 5:
            return 0.1
        elif request_rate < 20:
            return 0.3
        else:
            return 0.6

    def build_feature_vector(
        self,
        request_rate,
        cpu_usage,
        memory_usage
    ):
        """
        Combine all signals into final feature vector
        """

        cpu_demand, memory_demand = self.compute_demand(request_rate)
        heavy_ratio = self.compute_heavy_ratio(request_rate)

        feature = {
            "timestamp": time.time(),
            "request_rate": request_rate,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "cpu_demand": cpu_demand,
            "memory_demand": memory_demand,
            "heavy_ratio": heavy_ratio
        }

        return feature
