
import csv
import argparse

class SimProcess:
    def __init__(self, pid, arrival_time, burst_time, priority):
        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.priority = priority


def read_workload(filename):
    processes = []

    with open(filename, "r") as file:
        reader = csv.DictReader(file)

        for row in reader:
            p = SimProcess(
                row["pid"],
                int(row["arrival_time"]),
                int(row["burst_time"]),
                int(row["priority"])
            )
            processes.append(p)

    return processes


def fcfs_schedule(processes, quantum=None):
    current_time = 0
    results = []

    ordered = sorted(
        processes,
        key=lambda p: p.arrival_time
    )

    for p in ordered:
        start = max(current_time, p.arrival_time)
        completion = start + p.burst_time

        turnaround = completion - p.arrival_time
        waiting = turnaround - p.burst_time
        response = start - p.arrival_time

        results.append({
            "pid": p.pid,
            "waiting": waiting,
            "turnaround": turnaround,
            "response": response
        })

        current_time = completion

    return results


def sjf_schedule(processes, quantum=None):
    current_time = 0
    results = []
    remaining = processes.copy()

    while remaining:
        available = [
            p for p in remaining
            if p.arrival_time <= current_time
        ]

        if not available:
            current_time = min(
                p.arrival_time for p in remaining
            )
            continue

        p = min(
            available,
            key=lambda p: (p.burst_time, p.arrival_time)
        )

        start = current_time
        completion = start + p.burst_time

        turnaround = completion - p.arrival_time
        waiting = turnaround - p.burst_time
        response = start - p.arrival_time

        results.append({
            "pid": p.pid,
            "waiting": waiting,
            "turnaround": turnaround,
            "response": response
        })

        current_time = completion
        remaining.remove(p)

    return results


from collections import deque


def round_robin_schedule(processes, quantum=4):
    if quantum <= 0:
        raise ValueError("Quantum must be positive")

    current_time = 0
    results = []
    ready = deque()

    ordered = sorted(
        enumerate(processes),
        key=lambda x: (x[1].arrival_time, x[0])
    )

    remaining = {
        p.pid: p.burst_time for p in processes
    }
    first_start = {}
    completion_times = {}
    next_index = 0

    while len(completion_times) < len(processes):

        if not ready:
            if next_index < len(ordered):
                current_time = max(
                    current_time,
                    ordered[next_index][1].arrival_time
                )

        while (
            next_index < len(ordered)
            and ordered[next_index][1].arrival_time <= current_time
        ):
            ready.append(ordered[next_index][1])
            next_index += 1

        if not ready:
            continue

        p = ready.popleft()

        if p.pid not in first_start:
            first_start[p.pid] = current_time

        run_time = min(quantum, remaining[p.pid])
        current_time += run_time
        remaining[p.pid] -= run_time

        # Add processes that arrived during this time slice.
        while (
            next_index < len(ordered)
            and ordered[next_index][1].arrival_time <= current_time
        ):
            ready.append(ordered[next_index][1])
            next_index += 1

        if remaining[p.pid] > 0:
            ready.append(p)
        else:
            completion_times[p.pid] = current_time

    for p in processes:
        turnaround = completion_times[p.pid] - p.arrival_time
        waiting = turnaround - p.burst_time
        response = first_start[p.pid] - p.arrival_time

        results.append({
            "pid": p.pid,
            "waiting": waiting,
            "turnaround": turnaround,
            "response": response
        })

    return results

def priority_schedule(processes, quantum=None):
    current_time = 0
    results = []
    remaining = processes.copy()

    while remaining:
        available = [
            p for p in remaining
            if p.arrival_time <= current_time
        ]

        if not available:
            current_time = min(
                p.arrival_time for p in remaining
            )
            continue

        # Lower number means higher priority.
        # Ties follow the original input order.
        p = min(available, key=lambda p: p.priority)

        start = current_time
        completion = start + p.burst_time

        turnaround = completion - p.arrival_time
        waiting = turnaround - p.burst_time
        response = start - p.arrival_time

        results.append({
            "pid": p.pid,
            "waiting": waiting,
            "turnaround": turnaround,
            "response": response
        })

        current_time = completion
        remaining.remove(p)

    return results


def mlfq_schedule(processes, quantum=None):
    from collections import deque

    quantum_sizes = [4, 8, 16]
    boost_interval = 50

    queues = [deque() for _ in quantum_sizes]

    ordered = sorted(
        enumerate(processes),
        key=lambda x: (x[1].arrival_time, x[0])
    )

    remaining = {p.pid: p.burst_time for p in processes}
    budgets = {p.pid: quantum_sizes[0] for p in processes}

    first_start = {}
    completion_times = {}

    current_time = 0
    next_index = 0
    next_boost = boost_interval

    while len(completion_times) < len(processes):

        # Add processes that have arrived.
        while (next_index < len(ordered)
               and ordered[next_index][1].arrival_time <= current_time):
            p = ordered[next_index][1]
            queues[0].append(p)
            next_index += 1

        # Periodic priority boost.
        while current_time >= next_boost:
            waiting = []

            for q in queues:
                while q:
                    waiting.append(q.popleft())

            for p in waiting:
                queues[0].append(p)
                budgets[p.pid] = quantum_sizes[0]

            next_boost += boost_interval

        # If CPU is idle, jump to next arrival.
        if not any(queues):
            if next_index < len(ordered):
                current_time = ordered[next_index][1].arrival_time
                continue
            break

        level = next(i for i, q in enumerate(queues) if q)
        p = queues[level].popleft()

        if p.pid not in first_start:
            first_start[p.pid] = current_time

        run_time = min(
            remaining[p.pid],
            budgets[p.pid],
            next_boost - current_time
        )

        # Higher-priority arrival can preempt a lower queue.
        if level > 0 and next_index < len(ordered):
            next_arrival = ordered[next_index][1].arrival_time
            if current_time < next_arrival < current_time + run_time:
                run_time = next_arrival - current_time

        current_time += run_time
        remaining[p.pid] -= run_time
        budgets[p.pid] -= run_time

        # Record arrivals during execution.
        while (next_index < len(ordered)
               and ordered[next_index][1].arrival_time <= current_time):
            new_p = ordered[next_index][1]
            queues[0].append(new_p)
            next_index += 1

        if remaining[p.pid] == 0:
            completion_times[p.pid] = current_time

        elif current_time == next_boost:
            # Boost waiting processes and the running process.
            waiting = []

            for q in queues:
                while q:
                    waiting.append(q.popleft())

            waiting.append(p)

            for item in waiting:
                queues[0].append(item)
                budgets[item.pid] = quantum_sizes[0]

            # Priority Boost is handled above.
            next_boost += boost_interval

        elif budgets[p.pid] == 0:
            # Full quantum used: move to lower queue.
            new_level = min(level + 1, len(queues) - 1)
            budgets[p.pid] = quantum_sizes[new_level]
            queues[new_level].append(p)

        else:
            # Preempted early: keep the remaining quantum.
            queues[level].appendleft(p)

    results = []

    for p in processes:
        turnaround = completion_times[p.pid] - p.arrival_time
        waiting = turnaround - p.burst_time
        response = first_start[p.pid] - p.arrival_time

        results.append({
            "pid": p.pid,
            "waiting": waiting,
            "turnaround": turnaround,
            "response": response
        })

    return results



def main():
    parser = argparse.ArgumentParser(
        description="CPU Scheduling Simulator"
    )

    parser.add_argument(
        "--workload",
        default="sample.csv",
        help="CSV workload file"
    )

    parser.add_argument(
        "--algo",
        choices=["fcfs", "sjf", "rr", "priority", "mlfq"],
        help="Choose a scheduling algorithm"
    )

    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare all five algorithms"
    )

    parser.add_argument(
        "--quantum",
        type=int,
        default=4,
        help="Round Robin time quantum"
    )

    args = parser.parse_args()

    if args.quantum <= 0:
        parser.error("--quantum must be positive")

    if not args.compare and args.algo is None:
        parser.error("Choose --algo or --compare")

    processes = read_workload(args.workload)

    if not processes:
        parser.error("Workload cannot be empty")

    algorithms = {
        "fcfs": fcfs_schedule,
        "sjf": sjf_schedule,
        "rr": round_robin_schedule,
        "priority": priority_schedule,
        "mlfq": mlfq_schedule
    }

    def get_results(name):
        if name == "rr":
            return algorithms[name](
                processes, quantum=args.quantum
            )
        return algorithms[name](processes)

    def averages(results):
        count = len(results)
        return (
            sum(r["waiting"] for r in results) / count,
            sum(r["turnaround"] for r in results) / count,
            sum(r["response"] for r in results) / count
        )

    if args.compare:
        print("CPU Scheduling Comparison")
        print(
            f"{'Algorithm':<15}"
            f"{'Avg Waiting':<16}"
            f"{'Avg Turnaround':<18}"
            f"{'Avg Response':<15}"
        )

        for name in algorithms:
            results = get_results(name)
            w, t, r = averages(results)
            print(
                f"{name.upper():<15}"
                f"{w:<16.2f}"
                f"{t:<18.2f}"
                f"{r:<15.2f}"
            )

    else:
        results = get_results(args.algo)

        print(f"{args.algo.upper()} Scheduling Results")
        print("PID  Waiting  Turnaround  Response")

        for r in results:
            print(
                f"{r['pid']:<5}"
                f"{r['waiting']:<9}"
                f"{r['turnaround']:<12}"
                f"{r['response']}"
            )

        w, t, r = averages(results)

        print()
        print(f"Average Waiting Time: {w:.2f}")
        print(f"Average Turnaround Time: {t:.2f}")
        print(f"Average Response Time: {r:.2f}")


if __name__ == "__main__":
    main()


