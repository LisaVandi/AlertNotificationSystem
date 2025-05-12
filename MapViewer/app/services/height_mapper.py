"""
Z-Height Mapper Utility

This module provides functions to calculate height values based on floor levels
and translate between different coordinate spaces (real-world vs. model).
"""
import os
import math

class HeightMapper:
    def __init__(self, z_ranges: dict, scale_config: dict):
        self.base_z = z_ranges.get("base_z", 0)
        self.height_per_floor = z_ranges.get("height_per_floor", 3)
        self.z_start_at_floor_zero = z_ranges.get("z_start_at_floor_zero", True)
        self.scale_factor = scale_config.get("scale_factor", 200)
    
    def get_floor_height(self, floor_level):
        """
        Calculate the real-world height (in meters) for a given floor level
        
        Args:
            floor_level (int): The floor level
            
        Returns:
            float: Height in meters from ground level
        """
        if self.z_start_at_floor_zero:
            return self.base_z + (floor_level * self.height_per_floor)
        else:
            return self.base_z + ((floor_level - 1) * self.height_per_floor)
    
    def get_floor_z_range(self, floor_level):
        """
        Get the Z-coordinate range (min and max) for a given floor level
        
        Args:
            floor_level (int): The floor level
            
        Returns:
            tuple: (z_min, z_max) heights in meters
        """
        z_min = self.get_floor_height(floor_level)
        z_max = z_min + self.height_per_floor
        return (z_min, z_max)
    
    def get_floor_from_height(self, height):
        """
        Determine the floor level from a given height
        
        Args:
            height (float): Height in meters
            
        Returns:
            int: The floor level corresponding to the height
        """
        if self.z_start_at_floor_zero:
            normalized_height = height - self.base_z
            floor = math.floor(normalized_height / self.height_per_floor)
            return max(0, floor)  
        else:
            normalized_height = height - self.base_z
            floor = math.floor(normalized_height / self.height_per_floor) + 1
            return max(1, floor)
    
    def meters_to_model_units(self, meters):
        """
        Convert real-world meters to model units (centimeters)
        based on the scale factor
        
        Args:
            meters (float): Length in meters
            
        Returns:
            float: Length in model units (centimeters)
        """
        return meters * 100 / self.scale_factor
    
    def model_units_to_meters(self, units):
        """
        Convert model units (centimeters) to real-world meters
        based on the scale factor
        
        Args:
            units (float): Length in model units (centimeters)
            
        Returns:
            float: Length in meters
        """
        return units * self.scale_factor / 100
    
    def pixels_to_model_units(self, pixels, dpi=100):
        """
        Convert pixels to model units (centimeters).
        
        Args:
            pixels (float): Number of pixels.
            dpi (float): Dots per inch (pixels per inch, default 100).
            
        Returns:
            float: Length in model units (centimeters).
        """
        pixels_per_cm = dpi / 2.54  
        return pixels / pixels_per_cm