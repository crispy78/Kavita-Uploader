"""VirusTotal API v3 integration for malware scanning."""

import asyncio
import httpx
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from app.config import config
from app.logger import app_logger, scan_logger

# Store file loggers per scan
_file_loggers = {}


class VirusTotalScanner:
    """VirusTotal API v3 scanner implementation."""
    
    BASE_URL = "https://www.virustotal.com/api/v3"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize VirusTotal scanner.
        
        Args:
            api_key: VirusTotal API key (defaults to config)
        """
        self.api_key = api_key or config.scanning.virustotal_api_key
        if not self.api_key:
            app_logger.warning("VirusTotal API key not configured")
        
        self.headers = {
            "x-apikey": self.api_key,
            "Accept": "application/json"
        }
    
    async def check_hash(self, file_hash: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if file hash already exists in VirusTotal.
        
        Args:
            file_hash: SHA256 hash of file
            
        Returns:
            Tuple of (exists, report_data)
        """
        if not self.api_key:
            scan_logger.error("Cannot check hash: VirusTotal API key not configured")
            return False, None
        
        url = f"{self.BASE_URL}/files/{file_hash}"
        start_time = time.time()
        
        scan_logger.info(
            f"Checking hash in VirusTotal database",
            extra={
                "file_hash": file_hash,
                "scan_phase": "check_hash"
            }
        )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                duration_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    scan_logger.info(
                        f"✓ Hash found in VirusTotal - using existing report",
                        extra={
                            "file_hash": file_hash,
                            "scan_phase": "check_hash",
                            "status": "exists",
                            "duration_ms": duration_ms
                        }
                    )
                    return True, data
                elif response.status_code == 404:
                    scan_logger.info(
                        f"Hash not found - will upload for scanning",
                        extra={
                            "file_hash": file_hash,
                            "scan_phase": "check_hash",
                            "status": "not_found",
                            "duration_ms": duration_ms
                        }
                    )
                    return False, None
                else:
                    scan_logger.warning(
                        f"VirusTotal API error: {response.status_code}",
                        extra={
                            "file_hash": file_hash,
                            "scan_phase": "check_hash",
                            "status_code": response.status_code,
                            "response": response.text[:200],
                            "duration_ms": duration_ms
                        }
                    )
                    return False, None
                    
        except httpx.TimeoutException:
            scan_logger.error("VirusTotal API timeout during hash check", extra={"file_hash": file_hash, "scan_phase": "check_hash"})
            return False, None
        except Exception as e:
            scan_logger.error(
                f"Failed to check hash: {str(e)}",
                exc_info=True,
                extra={"file_hash": file_hash, "scan_phase": "check_hash"}
            )
            return False, None
    
    async def upload_file(self, file_path: str) -> Optional[str]:
        """Upload file to VirusTotal for scanning.
        
        Args:
            file_path: Path to file to upload
            
        Returns:
            Analysis ID if successful, None otherwise
        """
        if not self.api_key:
            scan_logger.error("Cannot upload file: VirusTotal API key not configured")
            return None
        
        url = f"{self.BASE_URL}/files"
        file_name = Path(file_path).name
        file_size = Path(file_path).stat().st_size
        start_time = time.time()
        
        scan_logger.info(
            f"Uploading file to VirusTotal ({file_size} bytes)",
            extra={
                "file_path": file_path,
                "file_size": file_size,
                "scan_phase": "upload"
            }
        )
        
        try:
            async with httpx.AsyncClient(timeout=config.scanning.virustotal_timeout) as client:
                with open(file_path, "rb") as f:
                    files = {"file": f}
                    response = await client.post(
                        url,
                        headers=self.headers,
                        files=files
                    )
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    analysis_id = data.get("data", {}).get("id")
                    
                    scan_logger.info(
                        f"✓ File uploaded successfully - analysis started",
                        extra={
                            "file_path": file_path,
                            "analysis_id": analysis_id,
                            "scan_phase": "upload",
                            "duration_ms": duration_ms
                        }
                    )
                    
                    return analysis_id
                else:
                    scan_logger.error(
                        f"✗ VirusTotal upload failed: {response.status_code}",
                        extra={
                            "file_path": file_path,
                            "scan_phase": "upload",
                            "status_code": response.status_code,
                            "response": response.text[:200],
                            "duration_ms": duration_ms
                        }
                    )
                    return None
                    
        except Exception as e:
            scan_logger.error(
                f"Failed to upload file: {str(e)}",
                exc_info=True,
                extra={"file_path": file_path, "scan_phase": "upload"}
            )
            return None
    
    async def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis results by ID.
        
        Args:
            analysis_id: Analysis ID from upload
            
        Returns:
            Analysis data if available, None otherwise
        """
        if not self.api_key:
            return None
        
        url = f"{self.BASE_URL}/analyses/{analysis_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    app_logger.warning(
                        f"Failed to get analysis: {response.status_code}",
                        extra={"analysis_id": analysis_id}
                    )
                    return None
                    
        except Exception as e:
            app_logger.error(
                f"Failed to get analysis: {str(e)}",
                exc_info=True,
                extra={"analysis_id": analysis_id}
            )
            return None
    
    async def poll_analysis(
        self,
        analysis_id: str,
        max_retries: Optional[int] = None,
        interval: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Poll for analysis completion.
        
        Args:
            analysis_id: Analysis ID to poll
            max_retries: Maximum polling attempts (defaults to config)
            interval: Seconds between polls (defaults to config)
            
        Returns:
            Completed analysis data or None if timeout
        """
        max_retries = max_retries or config.scanning.max_retries
        interval = interval or config.scanning.polling_interval_sec
        
        scan_logger.info(
            f"Polling for analysis results (checking every {interval}s, max {max_retries} attempts)",
            extra={
                "analysis_id": analysis_id,
                "scan_phase": "poll",
                "max_attempts": max_retries,
                "interval_sec": interval
            }
        )
        
        for attempt in range(1, max_retries + 1):
            data = await self.get_analysis(analysis_id)
            
            if not data:
                scan_logger.warning(
                    f"Failed to fetch analysis (attempt {attempt}/{max_retries})",
                    extra={
                        "analysis_id": analysis_id,
                        "scan_phase": "poll",
                        "attempt": attempt,
                        "max_attempts": max_retries
                    }
                )
                await asyncio.sleep(interval)
                continue
            
            status = data.get("data", {}).get("attributes", {}).get("status")
            
            if status == "completed":
                scan_logger.info(
                    f"✓ Analysis completed after {attempt} attempt(s)",
                    extra={
                        "analysis_id": analysis_id,
                        "scan_phase": "poll",
                        "attempt": attempt,
                        "max_attempts": max_retries
                    }
                )
                return data
            
            scan_logger.info(
                f"⏳ Analysis in progress... (attempt {attempt}/{max_retries}, status: {status})",
                extra={
                    "analysis_id": analysis_id,
                    "scan_phase": "poll",
                    "status": status,
                    "attempt": attempt,
                    "max_attempts": max_retries
                }
            )
            
            await asyncio.sleep(interval)
        
        scan_logger.warning(
            f"✗ Analysis timeout after {max_retries} attempts",
            extra={
                "analysis_id": analysis_id,
                "scan_phase": "poll",
                "max_attempts": max_retries
            }
        )
        return None
    
    def parse_analysis_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse VirusTotal analysis results into simplified format.
        
        Args:
            data: Raw VirusTotal API response
            
        Returns:
            Simplified scan results
        """
        try:
            attributes = data.get("data", {}).get("attributes", {})
            stats = attributes.get("stats", {})
            
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            undetected = stats.get("undetected", 0)
            harmless = stats.get("harmless", 0)
            total_engines = sum(stats.values())
            
            # Determine overall status
            if malicious > 0:
                status = "malicious"
            elif suspicious > 3:  # More than 3 suspicious engines
                status = "suspicious"
            elif undetected == total_engines:
                status = "undetected"
            else:
                status = "clean"
            
            # Get scan date
            scan_date = attributes.get("date", int(datetime.utcnow().timestamp()))
            
            # Get file hash
            file_hash = data.get("meta", {}).get("file_info", {}).get("sha256", "")
            
            result = {
                "status": status,
                "malicious_count": malicious,
                "suspicious_count": suspicious,
                "undetected_count": undetected,
                "harmless_count": harmless,
                "total_engines": total_engines,
                "scan_date": datetime.fromtimestamp(scan_date).isoformat(),
                "file_hash": file_hash,
                "virustotal_link": f"https://www.virustotal.com/gui/file/{file_hash}" if file_hash else None,
                "raw_stats": stats,
            }
            
            # Determine status emoji
            status_icon = {
                "clean": "✓",
                "malicious": "✗",
                "suspicious": "⚠",
                "undetected": "?",
                "error": "✗"
            }.get(status, "")
            
            scan_logger.info(
                f"{status_icon} Scan results: {status.upper()} - {malicious}/{total_engines} engines detected threats",
                extra={
                    "scan_phase": "complete",
                    "scan_result": status,
                    "malicious_count": malicious,
                    "suspicious_count": suspicious,
                    "total_engines": total_engines,
                    "file_hash": file_hash,
                    "virustotal_link": result["virustotal_link"]
                }
            )
            
            return result
            
        except Exception as e:
            app_logger.error(
                f"Failed to parse analysis results: {str(e)}",
                exc_info=True
            )
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def scan_file(
        self,
        file_path: str,
        file_hash: str,
        file_logger: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Complete scan workflow: check hash, upload if needed, poll results.
        
        Args:
            file_path: Path to file
            file_hash: SHA256 hash of file
            file_logger: Optional FileLogger for per-file logging
            
        Returns:
            Scan results dictionary
        """
        if not self.api_key:
            if file_logger:
                file_logger.log_error("VirusTotal API key not configured")
            return {
                "status": "error",
                "error": "VirusTotal API key not configured",
                "enabled": False
            }
        
        # Step 1: Check if hash already exists
        if config.scanning.auto_skip_known_hashes:
            if file_logger:
                file_logger.log_scan_progress("check_hash", "checking", {"hash": file_hash})
            
            exists, existing_data = await self.check_hash(file_hash)
            
            if exists and existing_data:
                if file_logger:
                    file_logger.log_scan_progress("check_hash", "found_existing", {
                        "message": "Using cached VirusTotal report"
                    })
                app_logger.info(
                    f"Using existing VirusTotal report for hash",
                    extra={"file_hash": file_hash}
                )
                return self.parse_analysis_results(existing_data)
            elif file_logger:
                file_logger.log_scan_progress("check_hash", "not_found", {
                    "message": "Hash not in VirusTotal database, uploading file"
                })
        
        # Step 2: Upload file for scanning
        if file_logger:
            file_logger.log_scan_progress("upload", "uploading", {
                "file_path": Path(file_path).name
            })
        
        analysis_id = await self.upload_file(file_path)
        
        if not analysis_id:
            if file_logger:
                file_logger.log_error("Failed to upload file to VirusTotal")
            return {
                "status": "error",
                "error": "Failed to upload file to VirusTotal"
            }
        
        if file_logger:
            file_logger.log_scan_progress("upload", "success", {
                "analysis_id": analysis_id
            })
        
        # Step 3: Poll for results
        if file_logger:
            file_logger.log_scan_progress("poll", "started", {
                "analysis_id": analysis_id,
                "interval": config.scanning.polling_interval_sec,
                "max_retries": config.scanning.max_retries
            })
        
        analysis_data = await self.poll_analysis(analysis_id)
        
        if not analysis_data:
            if file_logger:
                file_logger.log_scan_progress("poll", "timeout", {
                    "message": "Analysis timed out, check back later"
                })
            return {
                "status": "pending",
                "analysis_id": analysis_id,
                "message": "Analysis in progress, check back later"
            }
        
        if file_logger:
            file_logger.log_scan_progress("poll", "completed")
        
        # Step 4: Parse and return results
        results = self.parse_analysis_results(analysis_data)
        
        if file_logger:
            file_logger.log_scan_progress("complete", results.get("status", "unknown"), {
                "malicious_count": results.get("malicious_count", 0),
                "total_engines": results.get("total_engines", 0),
                "virustotal_link": results.get("virustotal_link")
            })
        
        return results

