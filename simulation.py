import random
import pandas as pd
import numpy as np
import math
from collections import deque


class Airplane:
    def __init__(self, id, min_fuel, max_fuel, min_arrival_time, max_arrival_time):
        self.id = id
        self.fuel_consumption_rate = random.uniform(5, 20)
        self.expected_landing_time = random.uniform(min_arrival_time, max_arrival_time)
        self.fuel_level = random.uniform(min_fuel, max_fuel)

        self.emergency_fuel = (self.fuel_consumption_rate * 60)
        self.fuel_level = max(self.fuel_level, self.emergency_fuel)
        self.fuel_level_final = self.fuel_level - self.emergency_fuel
        self.remaining_flying_time = self.fuel_level_final / self.fuel_consumption_rate

        self.is_urgent = self.fuel_level_final < self.emergency_fuel or self.remaining_flying_time < 1


def generate_airplane_stream(num_airplanes, min_fuel, max_fuel, min_arrival_time, max_arrival_time):
    return [Airplane(i, min_fuel, max_fuel, min_arrival_time, max_arrival_time) for i in range(1, num_airplanes + 1)]

"""
Schedule landings for airplanes based on their urgency and expected landing time.

@param airplane_stream: A stream of airplanes to be scheduled for landing.
@type airplane_stream: list[Airplane]
@return: A DataFrame containing the scheduled landing information including airplane ID, actual landing time,
         urgency status, and the landing strip assigned.
@rtype: pandas.DataFrame
"""

def schedule_landings(airplane_stream):
    urgent_airplanes = sorted([ap for ap in airplane_stream if ap.is_urgent],
                              key=lambda x: x.remaining_flying_time)
    non_urgent_airplanes = sorted([ap for ap in airplane_stream if not ap.is_urgent],
                                  key=lambda x: x.expected_landing_time)
    
    sorted_airplanes = urgent_airplanes + non_urgent_airplanes
    
    landing_schedule = []
    landing_strip_availability = [0, 0, 0]
    landing_strip_index = 0

    for airplane in sorted_airplanes:
        chosen_strip = landing_strip_index % 3
        next_available_time_with_gap = landing_strip_availability[chosen_strip] + 3/60
        actual_landing_time = max(airplane.expected_landing_time, next_available_time_with_gap)
        
        if airplane.is_urgent and actual_landing_time > airplane.remaining_flying_time:
            actual_landing_time = airplane.remaining_flying_time

        landing_strip_availability[chosen_strip] = actual_landing_time + 3
        landing_schedule.append((airplane.id, actual_landing_time, airplane.is_urgent, chosen_strip + 1))

        landing_strip_index += 1

    return pd.DataFrame(landing_schedule, columns=["Airplane ID", "Actual Landing Time", "Urgent", "Landing Strip"])


def evaluate_landing_schedule(landing_schedule_df, airplane_stream):
    for index, row in landing_schedule_df.iterrows():
        airplane = next((ap for ap in airplane_stream if ap.id == row['Airplane ID']), None)
        if airplane:
            difference = abs(airplane.expected_landing_time - row['Actual Landing Time'])
            urgency_penalty = 100 if airplane.is_urgent else 0
            score = 1000 - difference - urgency_penalty
            landing_schedule_df.at[index, 'Score'] = score

    total_score = landing_schedule_df['Score'].sum()
    return total_score


def get_successors(landing_schedule_df, airplane_stream): 
    if len(landing_schedule_df) <= 1:
        return [landing_schedule_df]
    successors = []
    for i in range(len(landing_schedule_df)): 
        for j in range(i + 1, len(landing_schedule_df)): 
            new_schedule_df = landing_schedule_df.copy()
            new_schedule_df.iloc[i], new_schedule_df.iloc[j] = new_schedule_df.iloc[j].copy(), new_schedule_df.iloc[i].copy()
            successors.append(new_schedule_df)
    return successors

"""
Generate a list of successor states (neighbours or solutions) for the hill climbing and tabu search algorithms.

This function generates a list of successor states by randomly swapping two planes in the landing schedule. It 
creates a copy of the current landing schedule, swaps two planes, and recalculates the actual landing time and 
scores for each plane in the new schedule.

The function uses a deque to simulate the availability of landing strips. It removes the strip that was just used 
and adds the time when the strip will become available again. The deque is then sorted to ensure the earliest 
available strip is always first.

The function repeats this process for a specified number of successors and returns the list of successor states.

@param landing_schedule_df: The current landing schedule.
@type landing_schedule_df: pandas.DataFrame
@param airplane_stream: A list of airplanes to schedule for landing.
@type airplane_stream: list[Airplane]
@param num_successors: The number of successors to generate. Default is 15.
@type num_successors: int, optional
@return: A list of successor states.
@rtype: list[pandas.DataFrame]
"""

def get_Hill_Tabu_successors(landing_schedule_df, airplane_stream, num_successors=15):
    successors = []
    num_planes = len(landing_schedule_df)
    for _ in range(num_successors):
        i, j = random.sample(range(num_planes), 2)  # Randomly choose two planes to swap
        new_schedule_df = landing_schedule_df.copy()
        new_schedule_df.iloc[i], new_schedule_df.iloc[j] = new_schedule_df.iloc[j].copy(), new_schedule_df.iloc[i].copy()
        # Recalculate the Actual Landing Time and the scores for each plane in the new schedule
        strip_availability_times = deque([0, 0, 0])  # Initialize with 3 strips all available at time 0
        for index, row in new_schedule_df.iterrows():
            airplane = next((ap for ap in airplane_stream if ap.id == row['Airplane ID']), None)
            if airplane:
                current_time = max(strip_availability_times[0], airplane.expected_landing_time)
                new_schedule_df.at[index, 'Actual Landing Time'] = current_time
                difference = abs(airplane.expected_landing_time - current_time)
                urgency_penalty = 100 if airplane.is_urgent else 0
                score = 1000 - difference - urgency_penalty
                new_schedule_df.at[index, 'Score'] = score
                strip_availability_times.popleft()  # Remove the strip that was just used
                strip_availability_times.append(current_time + 3)  # Add the time when the strip will become available again
                strip_availability_times = deque(sorted(strip_availability_times))  # Sort the times to ensure the earliest is always first
        successors.append(new_schedule_df)
    return successors


"""
Optimize the landing schedule for airplanes using a genetic algorithm.

This function applies a genetic algorithm to optimize the landing schedule for airplanes. Genetic algorithms are population-based metaheuristic optimization techniques inspired by the principles of natural selection and genetics.

The algorithm begins by generating an initial population of landing schedules using the 'generate_initial_schedule' function. It then iterates through a predefined number of generations, during each of which it evaluates the fitness of each individual (schedule) in the population.

In each generation, the algorithm selects parents based on their fitness scores, performs crossover to create offspring, and applies mutation to introduce genetic diversity. Elitism is implemented by preserving the best individuals from each generation.

After the main genetic algorithm loop, the function selects the top individuals from the best generations, replacing the worst individuals in the current population. It returns the best landing schedule found along with its corresponding score.

@param airplane_stream: A list of airplanes to schedule for landing.
@type airplane_stream: list[Airplane]
@param population_size: The size of the population. Default is 50.
@type population_size: int, optional
@param generations: The number of generations to run the genetic algorithm. Default is 50.
@type generations: int, optional
@param crossover_rate: The probability of crossover between parents. Default is 0.8.
@type crossover_rate: float, optional
@param mutation_rate: The probability of mutation for each gene. Default is 0.1.
@type mutation_rate: float, optional
@return: A tuple containing the best optimized landing schedule (DataFrame) and its corresponding score.
@rtype: tuple(pandas.DataFrame, float)
"""

class GeneticAlgorithmScheduler:
    def __init__(self, airplane_stream, population_size=50, generations=50, crossover_rate=0.8, mutation_rate=0.1):
        self.airplane_stream = airplane_stream
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.population = self.generate_initial_population()

    def generate_initial_population(self):
        return [self.generate_initial_schedule() for _ in range(self.population_size)]

    def generate_initial_schedule(self):
        shuffled_stream = random.sample(self.airplane_stream, len(self.airplane_stream))
        return schedule_landings(shuffled_stream)

    def calculate_fitness(self, schedule):
        return evaluate_landing_schedule(schedule, self.airplane_stream)

    def selection(self):
        fitness_scores = [self.calculate_fitness(schedule) for schedule in self.population]
        probabilities = 1 / (1 + np.array(fitness_scores))
        probabilities /= probabilities.sum()
        selected_indices = np.random.choice(range(len(self.population)), size=self.population_size, replace=False, p=probabilities)
        return [self.population[i] for i in selected_indices]

    def crossover(self, parent1, parent2):
        if random.random() < self.crossover_rate:
            crossover_point = random.randint(1, parent1.shape[0] - 2)
            child1 = pd.concat([parent1.iloc[:crossover_point], parent2.iloc[crossover_point:]]).reset_index(drop=True)
            child2 = pd.concat([parent2.iloc[:crossover_point], parent1.iloc[crossover_point:]]).reset_index(drop=True)
            return child1, child2
        else:
            return parent1, parent2

    def mutate(self, schedule):
        for index in range(len(schedule)):
            if random.random() < self.mutation_rate:
                replacement_plane = random.choice(self.airplane_stream)
                replacement_index = schedule[schedule['Airplane ID'] == replacement_plane.id].index[0]
                schedule.at[index, 'Actual Landing Time'], schedule.at[replacement_index, 'Actual Landing Time'] = schedule.at[replacement_index, 'Actual Landing Time'], schedule.at[index, 'Actual Landing Time']
        return schedule

    def run(self):
        best_score = float('inf')
        best_schedule = None
        stale_generations = 0

        for generation in range(self.generations):
            new_population = []
            parents = self.selection()

            while len(new_population) < self.population_size:
                parent1, parent2 = random.sample(parents, 2)
                child1, child2 = self.crossover(parent1, parent2)
                child1 = self.mutate(child1)
                child2 = self.mutate(child2)
                new_population.extend([child1, child2])

            self.population = new_population[:self.population_size]

            current_best_score = min([self.calculate_fitness(schedule) for schedule in self.population])
            if current_best_score < best_score:
                best_score = current_best_score
                best_schedule = self.population[[self.calculate_fitness(schedule) for schedule in self.population].index(best_score)]
                stale_generations = 0  
            else:
                stale_generations += 1 

            print(f"Generation {generation}: Best Score - {best_score}")

            if stale_generations >= 5:
                print("No improvement over the last 5 generations. Stopping early.")
                break

        return best_schedule, best_score

"""
Optimize the landing schedule for airplanes using hill climbing.

This function applies the hill climbing algorithm to improve the landing schedule for airplanes. Hill climbing is a 
local search algorithm that iteratively moves towards the best neighboring solution in the solution space.

The algorithm begins by determining if an airplane is urgent based on its fuel level and remaining flying time. It 
then generates an initial landing schedule using the 'schedule_landings' function and initializes the current score 
along with a list to store scores.

The function repeatedly explores neighboring landing schedules until no improvement is found. It selects the 
neighboring schedule with the lowest score, assuming it as the next state. If the next score is equal to the current 
score, indicating no improvement, the search terminates.

The function returns the optimized landing schedule.
@param airplane_stream: A list of airplanes to schedule for landing.
@type airplane_stream: list[Airplane]
@return: A tuple containing the optimized landing schedule (DataFrame) and an empty list of scores.
@rtype: tuple(pandas.DataFrame, list)
"""


def hill_climbing_schedule_landings(airplane_stream):
    

    # Mark urgent airplanes based on their fuel levels and expected landing times.
    for airplane in airplane_stream:
        airplane.is_urgent = (airplane.fuel_level_final < airplane.emergency_fuel or
                                airplane.remaining_flying_time < airplane.expected_landing_time)

    # Generate an initial landing schedule using the schedule_landings function.
    landing_schedule_df = schedule_landings(airplane_stream)

    # Initialize the current score and a list to store the scores of each iteration.
    current_score = evaluate_landing_schedule(landing_schedule_df, airplane_stream)
    scores = []

    # Repeat the following steps until no improvement is found.
    while True:
        #Get all neighboring landing schedules from the current schedule.
        neighbors = get_Hill_Tabu_successors(landing_schedule_df, airplane_stream)

        # Assume the next state is the same as the current state and track the lowest score.
        next_state_df = landing_schedule_df
        next_score = current_score

        # Iterate over the neighboring landing schedules and find the one with the lowest score.
        for neighbor_df in neighbors:
            score = evaluate_landing_schedule(neighbor_df, airplane_stream)
            if score < next_score:
                next_state_df = neighbor_df
                next_score = score

        if next_score == current_score:
            break

        landing_schedule_df = next_state_df
        current_score = next_score

    return landing_schedule_df, scores


"""
Optimize the landing schedule for airplanes using simulated annealing.

This function applies the simulated annealing algorithm to improve the landing schedule for airplanes. Simulated annealing is a technique inspired by metallurgy annealing, gradually reducing temperature to explore the solution space while avoiding local optima.

The algorithm begins with an initial landing schedule generated by 'schedule_landings'. It iteratively adjusts the schedule to improve its score, considering both better and worse solutions based on a probability function and current temperature.

@param airplane_stream: A list of airplanes to schedule for landing.
@type airplane_stream: list[Airplane]
@return: A tuple containing the optimized landing schedule (DataFrame) and its score.
@rtype: tuple(pandas.DataFrame, float)
"""


def simulated_annealing_schedule_landings(airplane_stream):
    def calculate_score(schedule_df, airplane_stream):
        for index, row in schedule_df.iterrows():
            airplane = next((ap for ap in airplane_stream if ap.id == row['Airplane ID']), None)
            if airplane:
                time_diff = abs(airplane.expected_landing_time - row['Actual Landing Time'])
                urgency_penalty = 100 if airplane.is_urgent else 0
                score = 1000 - time_diff - urgency_penalty
                schedule_df.at[index, 'Score'] = score
        return schedule_df

    def get_schedule_neighbor(schedule_df):
        neighbor_df = schedule_df.copy()
        i, j = random.sample(range(len(neighbor_df)), 2)
        neighbor_df.iloc[i], neighbor_df.iloc[j] = neighbor_df.iloc[j].copy(), neighbor_df.iloc[i].copy()
        return neighbor_df

    current_schedule = schedule_landings(airplane_stream)
    current_schedule = calculate_score(current_schedule, airplane_stream)
    current_score = current_schedule['Score'].sum()
    best_schedule = current_schedule
    best_score = current_score
    T = 1.0  # Initial high temperature
    T_min = 0.001  # Minimum temperature
    alpha = 0.9  # Cooling rate

    while T > T_min:
        new_schedule = get_schedule_neighbor(current_schedule)
        new_schedule = calculate_score(new_schedule, airplane_stream)
        new_score = new_schedule['Score'].sum()
        if new_score > current_score or math.exp((new_score - current_score) / T) > random.random():
            current_schedule = new_schedule
            current_score = new_score
            if new_score > best_score:
                best_schedule = new_schedule
                best_score = new_score
        T *= alpha  # Cool down

    return best_schedule, best_score

"""
Optimize the landing schedule for airplanes using tabu search.

This function applies the tabu search algorithm to improve the landing schedule for airplanes.

The algorithm begins by determining if an airplane is urgent based on its fuel level and remaining flying time. It 
then initializes variables, including the landing schedule, current score, a list of scores, and a tabu list.

The function iterates through the search process until it reaches the maximum number of iterations specified. During 
each iteration, it generates neighboring solutions from the current solution and evaluates their scores. It selects 
the best solution among neighbors and considers it for the next iteration while also considering solutions in the 
tabu list.

An aspiration criteria is used to allow the search to return to previously visited solutions if they offer a 
significant improvement. Additionally, a stochastic element is introduced by occasionally choosing a random neighbor 
as the next solution, which can help the search escape from local optima.

The search process continues until the maximum number of iterations is reached. The function returns the optimized 
landing schedule along with a list of scores recorded during the search process.

@param airplane_stream: A list of airplanes to schedule for landing.
@type airplane_stream: list[Airplane]
@param max_iterations: The maximum number of iterations for the tabu search algorithm. Default is 1000.
@type max_iterations: int, optional
@param max_tabu_size: The maximum size of the tabu list. Default is 10.
@type max_tabu_size: int, optional
@return: A tuple containing the optimized landing schedule (DataFrame) and a list of scores recorded during the search process.
@rtype: tuple(pandas.DataFrame, list[float])
"""

def tabu_search_schedule_landings(airplane_stream, max_iterations=1000, max_tabu_size=10):
    for airplane in airplane_stream:
        airplane.is_urgent = airplane.fuel_level_final < airplane.emergency_fuel or airplane.remaining_flying_time < airplane.expected_landing_time
    
    landing_schedule_df = schedule_landings(airplane_stream)
    current_score = evaluate_landing_schedule(landing_schedule_df, airplane_stream)
    scores = []
    tabu_list = []
    it = 0

    while it < max_iterations:
        neighbors = get_Hill_Tabu_successors(landing_schedule_df, airplane_stream)
        next_state_df = landing_schedule_df
        scores.append(current_score)
        next_score = current_score

        best_solution_df = landing_schedule_df
        best_solution_score = evaluate_landing_schedule(landing_schedule_df, airplane_stream)

        for neighbor_df in neighbors:
            neighbor_string = neighbor_df.to_string()
            score = evaluate_landing_schedule(neighbor_df, airplane_stream)
            if score < best_solution_score:
                best_solution_df = neighbor_df
                best_solution_score = score
            if neighbor_string not in tabu_list:
                if score < next_score:
                    next_state_df = neighbor_df
                    next_score = score
                tabu_list.append(neighbor_string) 
                if len(tabu_list) > max_tabu_size:
                    tabu_list.pop(0)

        if next_score >= current_score:
            if random.random() < 0.1:
                next_state_df = random.choice(neighbors)
                next_score = evaluate_landing_schedule(next_state_df, airplane_stream)
            else:
                next_state_df = best_solution_df
                next_score = best_solution_score

        landing_schedule_df = next_state_df
        current_score = next_score
        it += 1
    
    return landing_schedule_df, scores
