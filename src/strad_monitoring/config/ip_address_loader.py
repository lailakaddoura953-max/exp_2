"""
IP Address Loader - Load and validate strad to IP address mappings from JSON file

This module handles loading RTSP stream IP addresses for each strad ID from a
tab-separated JSON configuration file. It provides validation and easy lookup
of IP addresses for the automated video capture system.

Format:
    SC#\tIP_Address
    001\t192.168.1.100
    002\t192.168.1.101
    ...
    135\t192.168.1.234
"""

import json
import logging
import re
from typing import Dict, List, Optional
from pathlib import Path


logger = logging.getLogger(__name__)


class IPAddressLoader:
    """
    Load and validate strad to IP address mappings from JSON file.
    
    The file uses tab-separated values with SC# and IP_Address columns.
    Provides fast lookup and validation of IP addresses for monitoring cycle.
    """
    
    def __init__(self, json_path: str):
        """
        Load IP addresses from tab-separated JSON file.
        
        Args:
            json_path: Path to ip_addresses.json file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
            
        File Format:
            SC#\tIP_Address
            001\t192.168.1.100
            002\t192.168.1.101
        """
        self.json_path = json_path
        self.mappings: Dict[str, str] = {}
        self._load_file()
        logger.info(f"IPAddressLoader initialized with {len(self.mappings)} strad mappings")
    
    def _load_file(self) -> None:
        """
        Load and parse the IP address JSON file.
        
        File is expected to contain tab-separated SC# and IP_Address values.
        Skips header line if present (contains "SC#" or "SC" in first column).
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format is invalid
        """
        if not Path(self.json_path).exists():
            raise FileNotFoundError(f"IP addresses file not found: {self.json_path}")
        
        logger.debug(f"Loading IP addresses from: {self.json_path}")
        
        try:
            with open(self.json_path, 'r') as f:
                lines = f.readlines()
        except IOError as e:
            raise ValueError(f"Failed to read IP addresses file: {e}")
        
        if not lines:
            raise ValueError(f"IP addresses file is empty: {self.json_path}")
        
        line_num = 0
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip header line (if present)
            if line.startswith("SC#"):
                logger.debug(f"Skipping header line: {line}")
                continue
            
            # Parse tab-separated values
            try:
                parts = line.split('\t')
                if len(parts) != 2:
                    logger.warning(
                        f"Invalid format on line {line_num}: expected 2 tab-separated values, "
                        f"got {len(parts)} - skipping line"
                    )
                    continue
                
                sc_num, ip_address = parts[0].strip(), parts[1].strip()
                
                # Validate SC# format (should be 3 digits or SC followed by digits)
                if not self._validate_sc_num(sc_num):
                    logger.warning(f"Invalid SC# on line {line_num}: {sc_num} - skipping")
                    continue
                
                # Validate IP address format
                if not self._validate_ip_address(ip_address):
                    logger.warning(
                        f"Invalid IP address on line {line_num} for {sc_num}: {ip_address} - skipping"
                    )
                    continue
                
                # Store mapping (normalize SC# to have leading zeros)
                normalized_sc = self._normalize_sc_num(sc_num)
                self.mappings[normalized_sc] = ip_address
                logger.debug(f"Loaded: {normalized_sc} -> {ip_address}")
            
            except Exception as e:
                logger.warning(f"Error parsing line {line_num}: {e} - skipping")
                continue
        
        if not self.mappings:
            raise ValueError(f"No valid strad/IP mappings found in {self.json_path}")
        
        logger.info(f"Loaded {len(self.mappings)} strad/IP mappings")
    
    def _validate_sc_num(self, sc_num: str) -> bool:
        """
        Validate SC# format.
        
        Accepts:
        - 3-digit numbers: "001", "042", "135"
        - SC prefix + digits: "SC001", "SC042"
        
        Args:
            sc_num: SC number string to validate
            
        Returns:
            True if valid format, False otherwise
        """
        # Pattern: optional "SC" prefix, followed by 1-3 digits
        pattern = r'^(?:SC)?(\d{1,3})$'
        match = re.match(pattern, sc_num, re.IGNORECASE)
        return match is not None
    
    def _validate_ip_address(self, ip_address: str) -> bool:
        """
        Validate IP address format.
        
        Accepts IPv4 addresses in standard dotted-quad format.
        Examples: 192.168.1.100, 10.0.0.1, 172.16.0.1
        
        Args:
            ip_address: IP address string to validate
            
        Returns:
            True if valid IPv4 format, False otherwise
        """
        # IPv4 pattern: 1-3 digits, dot, repeated, last group 1-3 digits
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        
        if not re.match(pattern, ip_address):
            return False
        
        # Validate each octet is 0-255
        try:
            octets = [int(x) for x in ip_address.split('.')]
            return all(0 <= octet <= 255 for octet in octets)
        except (ValueError, AttributeError):
            return False
    
    def _normalize_sc_num(self, sc_num: str) -> str:
        """
        Normalize SC number to standard format (3-digit number).
        
        Converts:
        - "001" -> "001"
        - "42" -> "042"
        - "SC001" -> "001"
        - "SC042" -> "042"
        
        Args:
            sc_num: SC number to normalize
            
        Returns:
            Normalized SC number (3 digits)
        """
        # Extract digits from input
        digits = ''.join(c for c in sc_num if c.isdigit())
        # Pad with leading zeros to 3 digits
        return digits.zfill(3)
    
    def get_ip(self, strad_id: str) -> Optional[str]:
        """
        Get IP address for a strad ID.
        
        Args:
            strad_id: Strad ID (e.g., "SC001", "001", "42")
            
        Returns:
            IP address string if found, None otherwise
            
        Example:
            >>> loader = IPAddressLoader("config/ip_addresses.json")
            >>> ip = loader.get_ip("SC001")
            >>> print(ip)
            192.168.1.100
        """
        normalized_id = self._normalize_sc_num(strad_id)
        ip = self.mappings.get(normalized_id)
        
        if ip:
            logger.debug(f"Found IP for {strad_id}: {ip}")
        else:
            logger.warning(f"No IP address found for strad: {strad_id}")
        
        return ip
    
    def get_all_mappings(self) -> Dict[str, str]:
        """
        Get complete strad to IP address mapping dictionary.
        
        Returns:
            Dictionary with strad IDs as keys and IP addresses as values
            
        Example:
            >>> loader = IPAddressLoader("config/ip_addresses.json")
            >>> all_ips = loader.get_all_mappings()
            >>> print(all_ips)
            {'001': '192.168.1.100', '002': '192.168.1.101', ...}
        """
        return self.mappings.copy()
    
    def validate(self) -> List[str]:
        """
        Validate IP address mappings and connectivity.
        
        Performs basic validation:
        1. File exists and is readable
        2. Format is valid
        3. All SC# are unique
        4. All IP addresses are in valid format
        
        Returns:
            List of validation error messages (empty if valid)
            
        Note:
            Does NOT test actual network connectivity to each IP.
            That's done at capture time with retries.
        """
        errors = []
        
        # Check file exists
        if not Path(self.json_path).exists():
            errors.append(f"IP addresses file not found: {self.json_path}")
            return errors
        
        # Check file is readable
        if not Path(self.json_path).is_file():
            errors.append(f"IP addresses path is not a file: {self.json_path}")
            return errors
        
        # Check mappings loaded
        if not self.mappings:
            errors.append(f"No valid strad/IP mappings in {self.json_path}")
            return errors
        
        # Check for expected strad count (roughly)
        if len(self.mappings) < 10:
            errors.append(
                f"IP addresses file has {len(self.mappings)} mappings (expected ~135)"
            )
        
        # Check for duplicate IPs (warning only)
        ip_counts = {}
        for strad_id, ip in self.mappings.items():
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        duplicates = {ip: count for ip, count in ip_counts.items() if count > 1}
        if duplicates:
            logger.warning(f"Duplicate IP addresses found: {duplicates}")
        
        return errors
    
    def summary(self) -> str:
        """
        Get a summary of loaded IP address mappings.
        
        Returns:
            Human-readable summary string
        """
        if not self.mappings:
            return "No strad/IP mappings loaded"
        
        return (
            f"IP Address Loader Summary:\n"
            f"  File: {self.json_path}\n"
            f"  Mappings loaded: {len(self.mappings)}\n"
            f"  Range: SC{min(self.mappings.keys())} to SC{max(self.mappings.keys())}\n"
            f"  Example: SC001 -> {self.mappings.get('001', 'N/A')}"
        )
