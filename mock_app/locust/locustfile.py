from locust import HttpUser, task, between
import random

class LoadUser(HttpUser):
    wait_time = between(0.1, 1.0)

    @task
    def heavy_request(self):
        size = random.randint(5000, 20000)
        sleep = random.uniform(0.0, 0.1)
        self.client.get(f"/work?size={size}&sleep={sleep}")
