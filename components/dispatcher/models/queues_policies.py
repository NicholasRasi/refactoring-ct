import random
import statistics
import time
from enum import IntEnum


# Define how applications queues are managed
class QueuesPolicy(IntEnum):
    RANDOM = 0
    LONGEST_QUEUE = 1
    HEURISTIC_1 = 2


class QueuesPolicies:
    MAX_SAMPLE_SIZE = 50

    def __init__(self,
                 reqs_queues,
                 responses_list=None,
                 models=None,
                 logger=None) -> None:
        self.policies = {QueuesPolicy.RANDOM: self.policy_random,
                         QueuesPolicy.LONGEST_QUEUE: self.policy_longest_queue,
                         QueuesPolicy.HEURISTIC_1: self.policy_heuristic_1}
        self.reqs_queues = reqs_queues
        self.responses_list = responses_list
        self.models = {model.name: model for model in models}
        self.logger = logger

    def policy_random(self) -> str:
        return random.choice(list(self.reqs_queues.keys()))

    def policy_longest_queue(self) -> str:
        max_length = -1
        selected_model = list(self.reqs_queues.keys())[0]

        # compute the max
        for model in self.reqs_queues:
            if self.reqs_queues[model].qsize() > max_length:
                max_length = self.reqs_queues[model].qsize()
                selected_model = model

        return selected_model

        """
        # return a random queue between the ones with the same size
        queues_same_length = []
        for model in reqs_queues:
            print(reqs_queues[model].qsize())
            if reqs_queues[model].qsize() == max_length:
                queues_same_length.append(model)
            print(reqs_queues[model].qsize())

        return random.choice(queues_same_length)
        """

    def policy_heuristic_1(self) -> str:
        queue_lengths = {}
        avg_response_times = {}
        needs = {}

        for model in self.reqs_queues:
            queue_lengths[model] = (self.reqs_queues[model].qsize())

            if queue_lengths[model] == 0:
                avg_response_times[model] = 0
                needs[model] = 0
            else:
                response_times = [time.time() - req.ts_in for req in list(self.reqs_queues[model].queue)]
                log_response_time = [req.ts_out - req.ts_in for req in
                                     self.responses_list[model][-self.MAX_SAMPLE_SIZE:]]

                if not log_response_time:
                    avg_response_time = statistics.mean(response_times)
                else:
                    avg_response_time = statistics.mean(response_times) + statistics.mean(log_response_time)
                avg_response_times[model] = avg_response_time

                sla = self.models[model].sla
                alpha = self.models[model].alpha
                if avg_response_time < sla * alpha:
                    needs[model] = 0
                else:
                    needs[model] = avg_response_time - sla + ((1 - alpha) * sla)

        # if every model has needs == 0
        if max(needs.values()) == 0:
            # select the longest queue
            selected = max(queue_lengths, key=queue_lengths.get)
        else:
            # select the model with the higher need
            selected = max(needs, key=needs.get)
        return selected