'''
##############################################################
# Created Date: Friday, October 24th 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

from Run_SUMO_turn_online_check_function_v2 import (
    setup_sumo_environment, objective_function as fitness_func2
)
from onemodel_findpoints_online import online_optimization
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

from util_cali_turn_inflow import (
    update_turn_flow_from_solution,
    run_SUMO_create_EdgeData,
    run_jtrrouter_to_create_rou_xml,
    result_analysis_on_EdgeData,
    read_MatchupTable,
    generate_turn_demand_cali,
    generate_inflow,
    generate_turn_summary,)


def fitness_func_turn_flow(solution: list | np.ndarray, scenario_config: dict = None, **kwargs) -> float:
    """ Objective function for SUMO calibration, Run a single calibration iteration to get the best solution

    Args:
        solution (list | np.ndarray): the solution to evaluate.
        scenario_config (dict): the configuration for the scenario. Defaults to None.
        **kwargs: additional keyword arguments.
    Returns:
        float: the fitness value.
    """

    try:

        TurnDf_Calibration = scenario_config.get("TurnDf_Calibration")
        TurnToCalibrate = scenario_config.get("TurnToCalibrate")
        InflowDf_Calibration = scenario_config.get("InflowDf_Calibration")
        InflowEdgeToCalibrate = scenario_config.get("InflowEdgeToCalibrate")
        RealSummary_Calibration = scenario_config.get("RealSummary_Calibration")
        calibration_interval = scenario_config.get("calibration_interval", 60)
        demand_interval = scenario_config.get("demand_interval", 15)

        network_name = scenario_config.get("network_name")
        sim_start_time = scenario_config.get("sim_start_time")
        sim_end_time = scenario_config.get("sim_end_time")
        path_net = scenario_config.get("path_net")
        path_rou = pf.path2linux(Path(scenario_config.get("dir_turn_inflow")) / "route" / f"{network_name}.rou.xml")
        sim_name = scenario_config.get("sim_name")
        path_edge = pf.path2linux(Path(scenario_config.get("dir_turn_inflow")) / "EdgeData.xml")
        calibration_target = scenario_config.get("calibration_target")

        # TODO will remove in the future iteration - change current working dir at beginning of the calibration
        os.chdir(scenario_config.get("dir_turn_inflow"))

        # update turn and flow
        df_turn, df_inflow = update_turn_flow_from_solution(solution,
                                                            TurnDf_Calibration,
                                                            TurnToCalibrate,
                                                            InflowDf_Calibration,
                                                            InflowEdgeToCalibrate,
                                                            calibration_interval,
                                                            demand_interval)

        # update rou.xml from updated turn and flow in route and turn_flow folders
        run_jtrrouter_to_create_rou_xml(network_name,
                                        path_net,
                                        df_turn,
                                        df_inflow,
                                        path_rou,
                                        sim_start_time,
                                        sim_end_time)

        # run SUMO to get EdgeData.xml
        run_SUMO_create_EdgeData(sim_name, sim_end_time)

        # analyze EdgeData.xml to get best solution
        _, mean_GEH, GEH_percent = result_analysis_on_EdgeData(RealSummary_Calibration,
                                                               path_edge,
                                                               calibration_target,
                                                               sim_start_time,
                                                               sim_end_time)
        print(f"  :GEH: Mean Percentage: {mean_GEH}, {GEH_percent}")

        # minimize the negative percentage of GEH and the mean GEH
        # return [mean_GEH, -GEH_percent]

    except Exception:
        mean_GEH = float('inf')

    return [mean_GEH]


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

        self.obj_func = partial(fitness_func_turn_flow, scenario_config=self.scenario_config)

        # For turn inflow calibration,
        # lower bounds are 0 for all variables,
        # upper bounds are 1 for all variables except inflow variables
        # inflow variables have upper bounds as max_inflow in scenario_config["max_inflow"]
        self.bounds = ([0] * self.n_variable,
                       [1] * self.n_turn_variable + [self.max_inflow] * self.n_inflow_variable)

    def optimize(self, obj_func: callable = None):
        """ Perform Bayesian Optimization over multiple runs.

        Args:
            total_run (int): Number of optimization runs to perform.
            scenario_config (dict): Configuration for the scenario.
        """

        if isinstance(obj_func, callable):
            self.obj_func = obj_func
        else:
            raise TypeError("Objective function must be callable.")


        # get total_run from algo_config_turn_inflow
        total_run = self.algo_config_turn_inflow.get("bo_config", {}).get("total_run", 10)
        if not isinstance(total_run, int):
            raise TypeError("Total runs must be an integer.")
        if total_run <= 0 or total_run > 1000:
            raise ValueError("Total runs must be a positive integer less than or equal to 1000.")

        # Initialize min/max trackers
        param_mins = np.full(self.n_variable, np.inf)
        param_maxs = np.full(self.n_variable, -np.inf)
        fitness_global_min = np.inf
        fitness_global_max = -np.inf
        temp_evaluated_values = []
        temp_evaluated_points = []

        for run in range(total_run):
            print("  Starting SUMO-based Bayesian optimization...")
            print(f"  Dimensions: {self.n_variable}")
            print(f"  lb: {self.bounds[0]}, ub: {self.bounds[1]}")
            print(f"  Target: {self.target} with tolerance: {self.tolerance}")
            print(f"  Maximum evaluations: {self.max_evaluations}")

            start_time = time.time()

            # Run the optimization
            f_best, x_best, evaluated_points, evaluated_values = online_optimization(
                num_params=self.n_variable,
                variable_bounds=self.bounds,
                evaluation_function=partial(self.obj_func, scenario_config=scenario_config),
                tolerance=self.tolerance,
                target=self.target,
                random_points=self.random_points,
                max_evaluations=self.max_evaluations,
                kernel_type=self.kernel_type
            )

            end_time = time.time()
            elapsed_time = end_time - start_time
            self.run_times.append(elapsed_time)

            print("\n  Results:")
            print(f"  Best function value found: {f_best}")
            print(f"  Best point found: {x_best}")
            print(f"  Number of evaluations performed: {len(evaluated_values)}")
            print(f"  Elapsed time for run {run + 1}: {elapsed_time:.2f} seconds")

            temp_evaluated_values.append(evaluated_values)
            temp_evaluated_points.append(evaluated_points)

            # Update global fitness min/max
            fitness_global_min = min(fitness_global_min, np.min(evaluated_values))
            fitness_global_max = max(fitness_global_max, np.max(evaluated_values))

            # Update global param min/max
            evaluated_points_np = np.array(evaluated_points)
            param_mins = np.minimum(param_mins, np.min(evaluated_points_np, axis=0))
            param_maxs = np.maximum(param_maxs, np.max(evaluated_points_np, axis=0))

            # Record fitness and iteration for this run
            for iteration, (fitness, point) in enumerate(zip(evaluated_values, evaluated_points)):
                self.all_results.append({
                    'run': run + 1,
                    'iteration': iteration + 1,
                    'fitness': fitness,
                    'run_time_sec': elapsed_time if (iteration == len(evaluated_values) - 1) else ""
                })
                # Store parameter values for each iteration
                self.all_points.append({
                    'run': run + 1,
                    'iteration': iteration + 1,
                    **{f'param_{i + 1}': v for i, v in enumerate(point)},
                    'fitness': fitness,
                    'run_time_sec': elapsed_time if (iteration == len(evaluated_values) - 1) else ""
                })

            # After each run, print pass/fail for this run
            run_success = (f_best - self.target) <= self.tolerance
            if run_success:
                print(f"Run {run + 1}: Test PASSED! ✓ Found point {x_best} with value {f_best}")
            else:
                print(f"Run {run + 1}: Test FAILED! ✗ Could not reach target within tolerance. Best value: {f_best}")

        # Save all results to a DataFrame and CSV
        results_df = pd.DataFrame(self.all_results)
        # results_df.to_csv("sumo_bayesopt_10runs_results.csv", index=False)
        print("\nSaved all fitness and iteration results to sumo_bayesopt_10runs_results.csv")

        points_df = pd.DataFrame(self.all_points)
        # points_df.to_csv("sumo_bayesopt_10runs_points.csv", index=False)
        print("Saved all parameter values for each iteration to sumo_bayesopt_10runs_points.csv")

        # Create a DataFrame for best results per run (lowest fitness), including run time
        best_rows = []
        for run in range(1, total_run + 1):
            run_df = points_df[points_df['run'] == run]
            if not run_df.empty:
                best_idx = run_df['fitness'].idxmin()
                best_row = run_df.loc[best_idx].copy()
                # Ensure run_time_sec is filled for the best row
                best_row['run_time_sec'] = self.run_times[run - 1]
                best_rows.append(best_row)
        best_df = pd.DataFrame(best_rows)
        # best_df.to_csv("sumo_bayesopt_best_per_run.csv", index=False)
        print("Saved best fitness/iteration/parameters for each run to sumo_bayesopt_best_per_run.csv")

        # Plot fitness vs iteration for each run with fixed y-limits
        for run in range(total_run):
            evaluated_values = temp_evaluated_values[run]
            plt.figure(figsize=(8, 5))
            plt.plot(range(1, len(evaluated_values) + 1), evaluated_values, marker='o')
            plt.xlabel('Iteration')
            plt.ylabel('Fitness')
            plt.title(f'Fitness Convergence for Run {run + 1}')
            plt.ylim(fitness_global_min, fitness_global_max)
            plt.grid(True)
            plt.tight_layout()
            # plt.savefig(f'fitness_vs_iteration_run{run + 1}.png')
            plt.close()

        # Find the best run (lowest fitness)
        best_run_row = best_df.sort_values('fitness').iloc[0]
        best_run = best_run_row['run']
        best_fitness = best_run_row['fitness']
        print(f"\nBest run: {int(best_run)}")

        # Filter points for the best run
        best_run_fitness = results_df[results_df['run'] == best_run].sort_values('iteration')['fitness'].values

        # Plot fitness convergence for the best run and save (with fixed y-limits)
        plt.figure(figsize=(8, 5))
        plt.plot(range(1, len(best_run_fitness) + 1), best_run_fitness, marker='o')
        plt.xlabel('Iteration')
        plt.ylabel('Fitness')
        plt.title('Fitness Convergence for Best Run')
        plt.ylim(fitness_global_min, fitness_global_max)
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


if __name__ == "__main__":

    # Set up SUMO environment and get required data
    NetworkName, SimName, SimulationStartTime, SimulationEndTime, CalibrationTarget, CablibrationInterval, DemandInterval, ubc = setup_sumo_environment()
    TurnDf = pd.read_excel(
        r"C:\Users\xh8\ORNL_Work\github_workspace\Real-Twin RL\tests\bayesian_opt\cali_turn\Sumo\BeforeTurn\turn.xlsx")
    InflowDf = pd.read_excel(
        r"C:\Users\xh8\ORNL_Work\github_workspace\Real-Twin RL\tests\bayesian_opt\cali_turn\Sumo\BeforeTurn\inflow.xlsx")


    scenario_config = {
        "TurnDf_Calibration": TurnDf,

    }

    TurnDf_Calibration = scenario_config.get("TurnDf_Calibration")
    TurnToCalibrate = scenario_config.get("TurnToCalibrate")
    InflowDf_Calibration = scenario_config.get("InflowDf_Calibration")
    InflowEdgeToCalibrate = scenario_config.get("InflowEdgeToCalibrate")
    RealSummary_Calibration = scenario_config.get("RealSummary_Calibration")
    calibration_interval = scenario_config.get("calibration_interval", 60)
    demand_interval = scenario_config.get("demand_interval", 15)

    network_name = scenario_config.get("network_name")
    sim_start_time = scenario_config.get("sim_start_time")
    sim_end_time = scenario_config.get("sim_end_time")
    path_net = scenario_config.get("path_net")
    path_rou = pf.path2linux(Path(scenario_config.get("dir_turn_inflow")) / "route" / f"{network_name}.rou.xml")
    sim_name = scenario_config.get("sim_name")
    path_edge = pf.path2linux(Path(scenario_config.get("dir_turn_inflow")) / "EdgeData.xml")
    calibration_target = scenario_config.get("calibration_target")



    # Set up optimization parameters (adjust as needed)
    num_params = 14
    lower_bounds = np.array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.])
    upper_bounds = np.array([1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 200., 200., 200., 200.])
    variable_bounds = (lower_bounds, upper_bounds)
    tolerance = 3
    target = 0
    random_points = 4000
    max_evaluations = 100
    kernel_type = 'RBF'

    bo = BayesianOptimization(
        num_params=num_params,
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
        tolerance=tolerance,
        target=target,
        random_points=random_points,
        max_evaluations=max_evaluations,
        kernel_type=kernel_type
    )

    bo.optimize(total_run=10, output_dir=".")