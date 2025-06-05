"""
Navigation System - Path planning, SLAM, and autonomous navigation.
"""

import numpy as np
import time
from typing import Dict, List, Any, Optional, Tuple
from collections import deque

from utils.logger import setup_logger


class NavigationSystem:
    """Navigation system for autonomous robot movement."""
    
    def __init__(self, lidar_controller=None, vision_processor=None, config: Dict[str, Any] = None):
        """Initialize navigation system.
        
        Args:
            lidar_controller: LiDAR controller instance
            vision_processor: Vision processor instance
            config: Navigation configuration dictionary
        """
        self.logger = setup_logger(__name__)
        self.lidar_controller = lidar_controller
        self.vision_processor = vision_processor
        self.config = config or {}
        
        # Navigation state
        self.current_position = np.array([0.0, 0.0, 0.0])  # x, y, theta
        self.target_position = np.array([0.0, 0.0, 0.0])
        self.path: List[np.ndarray] = []
        self.is_navigating = False
        self.emergency_stop_active = False
        
        # SLAM components
        self.occupancy_map = None
        self.map_resolution = self.config.get('slam', {}).get('map_resolution', 0.05)
        self.map_size = self.config.get('slam', {}).get('map_size', [2000, 2000])
        
        # Safety parameters
        self.safety_margin = self.config.get('path_planning', {}).get('safety_margin', 0.3)
        self.min_obstacle_distance = 0.5  # meters
        
        # Initialize map
        self._initialize_map()
        
    def _initialize_map(self):
        """Initialize the occupancy grid map."""
        self.occupancy_map = np.ones(self.map_size, dtype=np.float32) * 0.5  # Unknown = 0.5
        self.map_origin = np.array([-self.map_size[0] * self.map_resolution / 2,
                                   -self.map_size[1] * self.map_resolution / 2])
        
    def update(self) -> Optional[Dict[str, Any]]:
        """Update navigation system and return movement command.
        
        Returns:
            Movement command dictionary or None
        """
        if self.emergency_stop_active:
            return {'velocities': {'base_rotation': 0, 'shoulder': 0, 'elbow': 0, 'wrist': 0}}
        
        # Update SLAM
        self._update_slam()
        
        # Check for obstacles
        if self._check_immediate_obstacles():
            self.logger.warning("Immediate obstacle detected, stopping")
            return {'velocities': {'base_rotation': 0, 'shoulder': 0, 'elbow': 0, 'wrist': 0}}
        
        # Execute navigation if active
        if self.is_navigating and len(self.path) > 0:
            return self._execute_path_following()
        
        return None
    
    def _update_slam(self):
        """Update SLAM (Simultaneous Localization and Mapping)."""
        if not self.lidar_controller:
            return
        
        # Get LiDAR scan data
        scan_data = self.lidar_controller.get_scan_data()
        if not scan_data:
            return
        
        # Update occupancy map with scan data
        for quality, angle, distance in scan_data:
            # Convert polar to Cartesian coordinates
            angle_rad = np.radians(angle)
            x = distance * np.cos(angle_rad)
            y = distance * np.sin(angle_rad)
            
            # Convert to map coordinates
            map_x = int((x - self.map_origin[0]) / self.map_resolution)
            map_y = int((y - self.map_origin[1]) / self.map_resolution)
            
            # Update map if within bounds
            if 0 <= map_x < self.map_size[0] and 0 <= map_y < self.map_size[1]:
                # Mark obstacle
                self.occupancy_map[map_y, map_x] = 1.0
                
                # Mark free space along the ray
                self._update_ray_casting(0, 0, map_x, map_y)
    
    def _update_ray_casting(self, x0: int, y0: int, x1: int, y1: int):
        """Update free space along a ray using Bresenham's line algorithm.
        
        Args:
            x0, y0: Start coordinates
            x1, y1: End coordinates
        """
        points = self._bresenham_line(x0, y0, x1, y1)
        
        for x, y in points[:-1]:  # Exclude the endpoint (obstacle)
            if 0 <= x < self.map_size[0] and 0 <= y < self.map_size[1]:
                # Mark as free space
                self.occupancy_map[y, x] = 0.0
    
    def _bresenham_line(self, x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
        """Bresenham's line algorithm for ray casting.
        
        Args:
            x0, y0: Start coordinates
            x1, y1: End coordinates
            
        Returns:
            List of points along the line
        """
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        x, y = x0, y0
        
        while True:
            points.append((x, y))
            
            if x == x1 and y == y1:
                break
                
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return points
    
    def _check_immediate_obstacles(self) -> bool:
        """Check for immediate obstacles in the robot's path.
        
        Returns:
            True if immediate obstacle detected, False otherwise
        """
        if not self.lidar_controller:
            return False
        
        # Check front sector for obstacles
        obstacles = self.lidar_controller.get_obstacles_in_direction(0, 30)  # Front 60-degree sector
        
        if obstacles and min(obstacles) < self.min_obstacle_distance:
            return True
        
        return False
    
    def set_target(self, x: float, y: float, theta: float = 0.0):
        """Set navigation target.
        
        Args:
            x: Target x coordinate
            y: Target y coordinate
            theta: Target orientation
        """
        self.target_position = np.array([x, y, theta])
        self.path = self._plan_path(self.current_position, self.target_position)
        
        if self.path:
            self.is_navigating = True
            self.logger.info(f"Path planned to target ({x}, {y}, {theta})")
        else:
            self.logger.warning("Failed to plan path to target")
    
    def _plan_path(self, start: np.ndarray, goal: np.ndarray) -> List[np.ndarray]:
        """Plan path from start to goal using A* algorithm.
        
        Args:
            start: Start position [x, y, theta]
            goal: Goal position [x, y, theta]
            
        Returns:
            List of waypoints
        """
        # Convert to map coordinates
        start_map = self._world_to_map(start[:2])
        goal_map = self._world_to_map(goal[:2])
        
        # Simple A* implementation
        path_map = self._a_star(start_map, goal_map)
        
        if not path_map:
            return []
        
        # Convert back to world coordinates
        path_world = []
        for point in path_map:
            world_point = self._map_to_world(point)
            path_world.append(np.array([world_point[0], world_point[1], 0.0]))
        
        return path_world
    
    def _a_star(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """A* pathfinding algorithm.
        
        Args:
            start: Start coordinates in map
            goal: Goal coordinates in map
            
        Returns:
            Path as list of coordinates
        """
        from heapq import heappush, heappop
        
        open_set = []
        heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self._heuristic(start, goal)}
        
        while open_set:
            current = heappop(open_set)[1]
            
            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            
            for neighbor in self._get_neighbors(current):
                if not self._is_valid_cell(neighbor):
                    continue
                
                tentative_g_score = g_score[current] + 1
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, goal)
                    heappush(open_set, (f_score[neighbor], neighbor))
        
        return []  # No path found
    
    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Heuristic function for A* (Manhattan distance).
        
        Args:
            a: First point
            b: Second point
            
        Returns:
            Heuristic distance
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def _get_neighbors(self, cell: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get neighboring cells for pathfinding.
        
        Args:
            cell: Current cell coordinates
            
        Returns:
            List of neighbor coordinates
        """
        x, y = cell
        neighbors = []
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                neighbors.append((x + dx, y + dy))
        
        return neighbors
    
    def _is_valid_cell(self, cell: Tuple[int, int]) -> bool:
        """Check if a cell is valid for pathfinding.
        
        Args:
            cell: Cell coordinates
            
        Returns:
            True if valid, False otherwise
        """
        x, y = cell
        
        # Check bounds
        if not (0 <= x < self.map_size[0] and 0 <= y < self.map_size[1]):
            return False
        
        # Check if cell is free (accounting for safety margin)
        safety_cells = int(self.safety_margin / self.map_resolution)
        
        for dx in range(-safety_cells, safety_cells + 1):
            for dy in range(-safety_cells, safety_cells + 1):
                check_x, check_y = x + dx, y + dy
                if (0 <= check_x < self.map_size[0] and 
                    0 <= check_y < self.map_size[1] and
                    self.occupancy_map[check_y, check_x] > 0.7):  # Occupied threshold
                    return False
        
        return True
    
    def _world_to_map(self, world_pos: np.ndarray) -> Tuple[int, int]:
        """Convert world coordinates to map coordinates.
        
        Args:
            world_pos: World position [x, y]
            
        Returns:
            Map coordinates (x, y)
        """
        map_x = int((world_pos[0] - self.map_origin[0]) / self.map_resolution)
        map_y = int((world_pos[1] - self.map_origin[1]) / self.map_resolution)
        return (map_x, map_y)
    
    def _map_to_world(self, map_pos: Tuple[int, int]) -> np.ndarray:
        """Convert map coordinates to world coordinates.
        
        Args:
            map_pos: Map coordinates (x, y)
            
        Returns:
            World position [x, y]
        """
        world_x = map_pos[0] * self.map_resolution + self.map_origin[0]
        world_y = map_pos[1] * self.map_resolution + self.map_origin[1]
        return np.array([world_x, world_y])
    
    def _execute_path_following(self) -> Dict[str, Any]:
        """Execute path following behavior.
        
        Returns:
            Movement command
        """
        if not self.path:
            self.is_navigating = False
            return {'velocities': {'base_rotation': 0, 'shoulder': 0, 'elbow': 0, 'wrist': 0}}
        
        # Get next waypoint
        next_waypoint = self.path[0]
        
        # Calculate distance to waypoint
        distance = np.linalg.norm(next_waypoint[:2] - self.current_position[:2])
        
        # If close enough to waypoint, move to next one
        if distance < 0.1:  # 10cm threshold
            self.path.pop(0)
            if not self.path:
                self.is_navigating = False
                self.logger.info("Target reached")
                return {'velocities': {'base_rotation': 0, 'shoulder': 0, 'elbow': 0, 'wrist': 0}}
        
        # Calculate movement command
        angle_to_target = np.arctan2(
            next_waypoint[1] - self.current_position[1],
            next_waypoint[0] - self.current_position[0]
        )
        
        angle_diff = angle_to_target - self.current_position[2]
        
        # Normalize angle difference
        while angle_diff > np.pi:
            angle_diff -= 2 * np.pi
        while angle_diff < -np.pi:
            angle_diff += 2 * np.pi
        
        # Simple proportional control
        angular_velocity = np.clip(angle_diff * 2.0, -1.0, 1.0)
        linear_velocity = np.clip(distance * 0.5, 0.0, 0.5) if abs(angle_diff) < 0.5 else 0.0
        
        # Convert to motor commands (simplified)
        return {
            'velocities': {
                'base_rotation': int(angular_velocity * 100),
                'shoulder': 0,
                'elbow': 0,
                'wrist': 0
            }
        }
    
    def emergency_stop(self):
        """Activate emergency stop."""
        self.emergency_stop_active = True
        self.is_navigating = False
        self.path.clear()
        self.logger.warning("Navigation emergency stop activated")
    
    def resume(self):
        """Resume navigation after emergency stop."""
        self.emergency_stop_active = False
        self.logger.info("Navigation resumed")
    
    def get_map(self) -> np.ndarray:
        """Get current occupancy map.
        
        Returns:
            Occupancy map as numpy array
        """
        return self.occupancy_map.copy()
    
    def shutdown(self):
        """Shutdown navigation system."""
        self.is_navigating = False
        self.path.clear()
        self.logger.info("Navigation system shutdown complete") 