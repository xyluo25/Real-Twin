'''
##############################################################
# Created Date: Monday, November 3rd 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

from time import time
import numpy as np
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import time
from functools import partial
import pyufunc as pf
from pathlib import Path

from ._bayesian_opt_util import online_optimization


class BayesianOptimization:
    """ Bayesian Optimization for calibrating turn inflow parameters. """

    def __init__(self, scenario_config: dict = None, algo_config_turn_inflow: dict = None, verbose: bool = False):
        """ Initialize the Bayesian Optimization class.

        Args:
            scenario_config (dict): Configuration for the scenario.
            algo_config_turn_inflow (dict): Algorithm configuration for turn inflow calibration.
            verbose (bool): Whether to print verbose output.
        """

        self.scenario_config = scenario_config
        self.algo_config_turn_inflow = algo_config_turn_inflow
        self.verbose = verbose

        self.n_variable = self.scenario_config.get("N_Variable")
        self.n_inflow_variable = self.scenario_config.get("N_InflowVariable")
        self.n_turn_variable = self.scenario_config.get("N_TurnVariable")
        # max inflow for the inflow variables
        self.max_inflow = self.scenario_config.get("max_inflow", 200)

        # self.obj_func = partial(fitness_func_turn_flow, scenario_config=self.scenario_config)

        # For turn inflow calibration,
        # lower bounds are 0 for all variables,
        # upper bounds are 1 for all variables except inflow variables
        # inflow variables have upper bounds as max_inflow in scenario_config["max_inflow"]
        self.bounds = ([0] * self.n_variable,
                       [1] * self.n_turn_variable + [self.max_inflow] * self.n_inflow_variable)

    def solve(self, obj_func: callable = None):
        """ Perform Bayesian Optimization over multiple runs.

        Args:
            obj_func (callable): Objective function to minimize.
                # obj_func = partial(fitness_func_turn_flow, scenario_config=self.scenario_config)
        """
        # get total_run from algo_config_turn_inflow
        total_run = self.algo_config_turn_inflow.get("bo_config", {}).get("total_run", 10)
        if not isinstance(total_run, int):
            raise TypeError("Total runs must be an integer.")
        if total_run <= 0 or total_run > 1000:
            raise ValueError("Total runs must be a positive integer less than or equal to 1000.")

        self.kernel_type = self.algo_config_turn_inflow.get("bo_config", {}).get("kernel_type", "RBF")
        self.tolerance = self.algo_config_turn_inflow.get("bo_config", {}).get("tolerance", 3)
        self.target = self.algo_config_turn_inflow.get("bo_config", {}).get("target", 0)
        self.random_points = self.algo_config_turn_inflow.get("bo_config", {}).get("random_points", 4000)
        self.max_evaluations = self.algo_config_turn_inflow.get("bo_config", {}).get("max_evaluations", 100)

        # Initialize min/max trackers
        all_results = []
        all_points = []
        run_times = []

        param_mins = np.full(self.n_variable, np.inf)
        param_maxs = np.full(self.n_variable, -np.inf)
        self.fitness_global_min = np.inf
        self.fitness_global_max = -np.inf
        self.temp_evaluated_values = []
        temp_evaluated_points = []

        print("  :Starting SUMO-based Bayesian optimization...")
        # print(f"  :Dimensions: {self.n_variable}")
        print(f"  :lb: {self.bounds[0]}, ub: {self.bounds[1]}")
        print(f"  :Target: {self.target} with tolerance: {self.tolerance}")
        print(f"  :Maximum evaluations: {self.max_evaluations}")

        for run in range(total_run):
            print(f"\n  Run {run + 1} of {total_run}")

            start_time = time.time()
            # Run the optimization
            f_best, x_best, evaluated_points, evaluated_values = online_optimization(
                num_params=self.n_variable,
                variable_bounds=self.bounds,
                evaluation_function=partial(obj_func, scenario_config=self.scenario_config),
                tolerance=self.tolerance,
                target=self.target,
                random_points=self.random_points,
                max_evaluations=self.max_evaluations,
                kernel_type=self.kernel_type
            )

            end_time = time.time()
            elapsed_time = end_time - start_time
            run_times.append(elapsed_time)

            print("\n  Results:")
            print(f"  :Best function value found: {f_best}")
            print(f"  :Best point found: {x_best}")
            print(f"  :Number of evaluations performed: {len(evaluated_values)}")
            print(f"  :Elapsed time for run {run + 1}: {elapsed_time:.2f} seconds")

            self.temp_evaluated_values.append(evaluated_values)
            temp_evaluated_points.append(evaluated_points)

            # Update global fitness min/max
            self.fitness_global_min = min(self.fitness_global_min, np.min(evaluated_values))
            self.fitness_global_max = max(self.fitness_global_max, np.max(evaluated_values))

            # Update global param min/max
            evaluated_points_np = np.array(evaluated_points)
            param_mins = np.minimum(param_mins, np.min(evaluated_points_np, axis=0))
            param_maxs = np.maximum(param_maxs, np.max(evaluated_points_np, axis=0))

            # Record fitness and iteration for this run
            for iteration, (fitness, point) in enumerate(zip(evaluated_values, evaluated_points)):

                fitness = fitness if not isinstance(fitness, list) else fitness[0]
                all_results.append({
                    'run': run + 1,
                    'iteration': iteration + 1,
                    'fitness': fitness,
                    'run_time_sec': elapsed_time if (iteration == len(evaluated_values) - 1) else ""
                })
                # Store parameter values for each iteration
                all_points.append({
                    'run': run + 1,
                    'iteration': iteration + 1,
                    **{f'param_{i + 1}': v for i, v in enumerate(point)},
                    'fitness': fitness,
                    'run_time_sec': elapsed_time if (iteration == len(evaluated_values) - 1) else ""
                })

            # After each run, print pass/fail for this run
            if isinstance(f_best, list):
                f_best = f_best[0]

            run_success = (f_best - self.target) <= self.tolerance
            if run_success:
                print(f"Run {run + 1}: Test PASSED! ✓ Found point {x_best} with value {f_best}")
            else:
                print(f"Run {run + 1}: Test FAILED! ✗ Could not reach target within tolerance. Best value: {f_best}")

        # Save all results to a DataFrame and CSV
        self.results_df = pd.DataFrame(all_results)
        # results_df.to_csv("sumo_bayesopt_10runs_results.csv", index=False)
        print("\nSaved all fitness and iteration results to sumo_bayesopt_10runs_results.csv")

        self.points_df = pd.DataFrame(all_points)
        # points_df.to_csv("sumo_bayesopt_10runs_points.csv", index=False)
        print("Saved all parameter values for each iteration to sumo_bayesopt_10runs_points.csv")

        # Create a DataFrame for best results per run (lowest fitness), including run time
        best_rows = []
        for run in range(1, total_run + 1):
            run_df = self.points_df[self.points_df['run'] == run]
            if not run_df.empty:
                best_idx = run_df['fitness'].idxmin()
                best_row = run_df.loc[best_idx].copy()
                # Ensure run_time_sec is filled for the best row
                best_row['run_time_sec'] = run_times[run - 1]
                best_rows.append(best_row)
        self.best_df = pd.DataFrame(best_rows)
        # best_df.to_csv("sumo_bayesopt_best_per_run.csv", index=False)
        print("Saved best fitness/iteration/parameters for each run to sumo_bayesopt_best_per_run.csv")

        # Plot fitness vs iteration for each run with fixed y-limits
        for run in range(total_run):
            evaluated_values = self.temp_evaluated_values[run]
            plt.figure(figsize=(8, 5))
            plt.plot(range(1, len(evaluated_values) + 1), evaluated_values, marker='o')
            plt.xlabel('Iteration')
            plt.ylabel('Fitness')
            plt.title(f'Fitness Convergence for Run {run + 1}')
            plt.ylim(self.fitness_global_min, self.fitness_global_max)
            plt.grid(True)
            plt.tight_layout()
            # plt.savefig(f'fitness_vs_iteration_run{run + 1}.png')
            plt.close()

        # Find the best run (lowest fitness)
        best_run_row = self.best_df.sort_values('fitness').iloc[0]
        best_run = best_run_row['run']
        best_fitness = best_run_row['fitness']
        print(f"\nBest run: {int(best_run)}")

        # Filter points for the best run
        self.best_run_fitness = self.results_df[self.results_df['run'] == best_run].sort_values('iteration')['fitness'].values

        # Plot fitness convergence for the best run and save (with fixed y-limits)
        plt.figure(figsize=(8, 5))
        plt.plot(range(1, len(self.best_run_fitness) + 1), self.best_run_fitness, marker='o')
        plt.xlabel('Iteration')
        plt.ylabel('Fitness')
        plt.title('Fitness Convergence for Best Run')
        plt.ylim(self.fitness_global_min, self.fitness_global_max)
        plt.grid(True)
        plt.tight_layout()
        # plt.savefig('best_run_fitness_convergence.png')
        plt.close()

        # Test passed/failed message for best run
        success = (best_fitness - self.target) <= self.tolerance
        if success:
            print("\nTest PASSED! ✓")
        else:
            print("\nTest FAILED! ✗")
            print(f"Could not reach target within tolerance. Best value: {best_fitness}")

        return None

    def run_vis(self, output_dir: str = "./"):
        """ Visualize the results of the Bayesian Optimization. """

        # save data to local

        self.results_df.to_csv(os.path.join(output_dir, "sumo_bayesopt_10runs_results.csv"), index=False)
        print("\nSaved all fitness and iteration results to sumo_bayesopt_10runs_results.csv")

        self.points_df.to_csv(os.path.join(output_dir, "sumo_bayesopt_10runs_points.csv"), index=False)
        print("Saved all parameter values for each iteration to sumo_bayesopt_10runs_points.csv")

        self.best_df.to_csv(os.path.join(output_dir, "sumo_bayesopt_best_per_run.csv"), index=False)
        print("Saved best fitness/iteration/parameters for each run to sumo_bayesopt_best_per_run.csv")

        # Plot fitness vs iteration for each run with fixed y-limits
        total_run = self.algo_config_turn_inflow.get("bo_config", {}).get("total_run", 10)
        for run in range(total_run):
            evaluated_values = self.temp_evaluated_values[run]
            plt.figure(figsize=(8, 5))
            plt.plot(range(1, len(evaluated_values) + 1), evaluated_values, marker='o')
            plt.xlabel('Iteration')
            plt.ylabel('Fitness')
            plt.title(f'Fitness Convergence for Run {run + 1}')
            plt.ylim(self.fitness_global_min, self.fitness_global_max)
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f'fitness_vs_iteration_run{run + 1}.png'))
            plt.close()

        # Find the best run (lowest fitness)
        best_run_row = self.best_df.sort_values('fitness').iloc[0]
        best_run = best_run_row['run']
        print(f"\nBest run: {int(best_run)}")

        # Filter points for the best run
        best_run_fitness = self.results_df[self.results_df['run'] == best_run].sort_values('iteration')[
            'fitness'].values

        # Plot fitness convergence for the best run and save (with fixed y-limits)
        plt.figure(figsize=(8, 5))
        plt.plot(range(1, len(best_run_fitness) + 1), best_run_fitness, marker='o')
        plt.xlabel('Iteration')
        plt.ylabel('Fitness')
        plt.title('Fitness Convergence for Best Run')
        plt.ylim(self.fitness_global_min, self.fitness_global_max)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'best_run_fitness_convergence.png'))
        plt.close()
