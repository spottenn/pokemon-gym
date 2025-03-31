from benchflow import BaseBench
from benchflow.BaseBench import BenchmarkResult
from benchflow.schemas import BenchArgs
from typing import Dict, Any
import os

class PokemonBench(BaseBench):
    def get_args(self, task_id: str) -> BenchArgs:
        arguments = {
            "required": [""],
            "optional": {"EVAL_TIME": 30 * 60},
        }
        return BenchArgs(arguments)
    
    def get_image_name(self) -> str:
        return "pokemon"
    
    def get_results_dir_in_container(self) -> str:
        return "/app/results"
    
    def get_log_files_dir_in_container(self) -> str:
        return "/app/logs"
    
    def get_result(self, task_id: str) -> BenchmarkResult:
        results_dir = os.path.join(self.results_dir, task_id)
        log_dir = os.path.join(self.log_files_dir, task_id)
        return BenchmarkResult(
            is_resolved=True,
            message="",
        )
    
    def get_all_tasks(self, split: str) -> Dict[str, Any]:
        return {
            "task_ids": ["0"],
            "error_message": None,
        }
