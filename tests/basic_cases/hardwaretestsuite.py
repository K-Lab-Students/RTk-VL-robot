from abc import ABC, abstractmethod
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable

from src.utils.logger import setup_logger


logger = setup_logger(__name__)
class HardwareTestSuite(ABC):
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = setup_logger(name)
        self.tests_results : List[Tuple[str, bool, str]] = []
        self.setup_complete = False

    @abstractmethod
    def setup_hardware(self) -> bool:
        "Setup the hardware for the tests"
        pass

    @abstractmethod
    def cleanup_hardware(self) -> None:
        "Cleanup after the tests"
        pass

    @abstractmethod
    def test_basic_functionality(self) -> bool:
        "Test to check the basic functionality of the hardware"
        pass
    
    @abstractmethod
    def test_error_handling(self) -> bool:
        "Test to check the error handling of the hardware"
        pass
    
    @abstractmethod
    def test_performance(self) -> bool:
        "Test to measure the performance of the hardware"
        pass


    def _record_test_result(self, test_name: str, passed: bool, message: str):
        self.tests_results.append((test_name, passed, message))
        status = "✅" if passed else "❌"
        self.logger.info(f"{status} {test_name}: {message}")

    def _report_results(self, test_name: str, test_func: Callable):
        self.logger.info(f"Running test: {test_name}")
        try:
            result = test_func()
            self._record_test_result(test_name, result, "Test passed")
            return result
        except Exception as e:
            self._record_test_result(test_name, False, f"Test failed: {str(e)}")
            return False

    def run_all_tests(self):
        if not self.setup_hardware():
            self.logger.error(f"Setup failed for {self.name}")
            return False
        self.setup_complete = True
        try:
            self.logger.info(f"Running tests for {self.name}")
            self._report_results("Basic Functionality", self.test_basic_functionality)
            self._report_results("Error Handling", self.test_error_handling)
            self._report_results("Performance", self.test_performance)
        finally:
            self.cleanup_hardware()
            self.setup_complete = False
        return self._report_summary()
    
    def _report_summary(self) -> bool:
        passed = sum(1 for test in self.tests_results if test[1])
        total = len(self.tests_results)
        
        self.logger.info(f"Test Summary for {self.name}")
        self.logger.info(f"Total tests: {total}\nPassed: {passed}\nFailed: {total - passed}")
        for test_name, passed, message in self.tests_results:
            status = "✅" if passed else "❌"
            self.logger.info(f"{status} {test_name}: {message}")
        return passed == total