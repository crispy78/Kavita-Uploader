"""Kavita API client for fetching library information."""

import httpx
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.config import config
from app.logger import app_logger


class KavitaAPIClient:
    """Client for interacting with Kavita API."""
    
    def __init__(self):
        self.kavita_url = config.kavita.server_url.rstrip('/')
        self.verify_ssl = config.kavita.verify_ssl
        self.timeout = config.kavita.timeout
        self.api_key = config.kavita.api_key if config.kavita.use_api_key else None
        self._libraries_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 300  # Cache for 5 minutes
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        headers = {}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def get_libraries(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch libraries from Kavita API.
        
        Results are cached for 5 minutes to reduce API calls.
        
        Args:
            force_refresh: Force cache refresh even if cached
            
        Returns:
            List of library dictionaries with paths and metadata
            
        Raises:
            HTTPException: If API call fails
        """
        import time
        
        # Check cache first
        if not force_refresh and self._libraries_cache is not None and self._cache_timestamp:
            if time.time() - self._cache_timestamp < self._cache_ttl:
                app_logger.debug(
                    f"Returning cached libraries",
                    extra={"count": len(self._libraries_cache)}
                )
                return self._libraries_cache
        
        if not config.kavita.enabled:
            app_logger.warning("Kavita is not enabled, cannot fetch libraries")
            return []
        
        try:
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=self.timeout) as client:
                # Use the documented Kavita API endpoint: /api/Library/list
                # Reference: https://www.kavitareader.com/docs/api/
                url = f"{self.kavita_url}/api/Library/list"
                headers = self._get_auth_headers()
                
                app_logger.debug(
                    f"Fetching libraries from Kavita API",
                    extra={"url": url}
                )
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Handle different response formats
                    libraries = data if isinstance(data, list) else data.get("data", data.get("libraries", []))
                    
                    # Extract library paths from Kavita API response
                    library_list = []
                    for lib in libraries:
                        if isinstance(lib, dict):
                            # Kavita API returns libraries with folders array
                            # Each library can have multiple folders (rootFolders or folders field)
                            folders = lib.get("folders") or lib.get("rootFolders") or lib.get("folderPaths") or []
                            
                            if isinstance(folders, list):
                                for folder in folders:
                                    if isinstance(folder, dict):
                                        # Folder object with path property
                                        folder_path = folder.get("path") or folder.get("folder") or folder.get("folderPath")
                                        if folder_path:
                                            library_list.append({
                                                "id": lib.get("id"),
                                                "name": lib.get("name", "Unknown"),
                                                "path": folder_path,
                                                "type": lib.get("type", lib.get("libraryType", "Unknown"))
                                            })
                                    elif isinstance(folder, str):
                                        # Folder is just a path string
                                        library_list.append({
                                            "id": lib.get("id"),
                                            "name": lib.get("name", "Unknown"),
                                            "path": folder,
                                            "type": lib.get("type", lib.get("libraryType", "Unknown"))
                                        })
                            else:
                                # Single folder path
                                folder_path = folders if isinstance(folders, str) else None
                                if folder_path:
                                    library_list.append({
                                        "id": lib.get("id"),
                                        "name": lib.get("name", "Unknown"),
                                        "path": folder_path,
                                        "type": lib.get("type", lib.get("libraryType", "Unknown"))
                                    })
                            
                            # If no folders found but library has a direct path
                            if not library_list or not any(l.get("id") == lib.get("id") for l in library_list):
                                direct_path = lib.get("path") or lib.get("folderPath")
                                if direct_path:
                                    library_list.append({
                                        "id": lib.get("id"),
                                        "name": lib.get("name", "Unknown"),
                                        "path": direct_path,
                                        "type": lib.get("type", lib.get("libraryType", "Unknown"))
                                    })
                        elif isinstance(lib, str):
                            # If library is just a path string
                            library_list.append({
                                "path": lib,
                                "name": lib,
                                "id": None,
                                "type": "Unknown"
                            })
                    
                    # Cache the results
                    self._libraries_cache = library_list
                    self._cache_timestamp = time.time()
                    
                    app_logger.info(
                        f"Fetched {len(library_list)} libraries from Kavita API",
                        extra={"libraries": library_list}
                    )
                    
                    return library_list
                elif response.status_code == 401:
                    app_logger.error(
                        f"Kavita API authentication failed",
                        extra={"status": response.status_code, "url": url}
                    )
                    raise HTTPException(
                        status_code=503,
                        detail="Unable to authenticate with Kavita API. Check your API key or credentials."
                    )
                else:
                    error_text = response.text[:200] if response.text else "No error details"
                    app_logger.error(
                        f"Failed to fetch libraries from Kavita API",
                        extra={"status": response.status_code, "error": error_text, "url": url}
                    )
                    raise HTTPException(
                        status_code=503,
                        detail=f"Unable to fetch libraries from Kavita API: Status {response.status_code}"
                    )
                
        except HTTPException:
            raise
        except Exception as e:
            app_logger.error(
                f"Error fetching libraries from Kavita API: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=503,
                detail=f"Error fetching libraries from Kavita: {str(e)}"
            )
    
    async def get_library_paths(self, force_refresh: bool = False) -> List[str]:
        """Get list of library paths from Kavita API.
        
        Convenience method that returns just the paths.
        
        Args:
            force_refresh: Force cache refresh
            
        Returns:
            List of library directory paths
        """
        libraries = await self.get_libraries(force_refresh=force_refresh)
        paths = [lib["path"] for lib in libraries if lib.get("path")]
        
        # Resolve relative paths if needed
        resolved_paths = []
        for path in paths:
            try:
                import os
                resolved = os.path.abspath(os.path.expanduser(path))
                if os.path.exists(resolved) or os.path.isabs(path):
                    resolved_paths.append(resolved)
                else:
                    app_logger.warning(
                        f"Library path does not exist, skipping",
                        extra={"path": path, "resolved": resolved}
                    )
            except Exception as e:
                app_logger.warning(
                    f"Error resolving library path: {path}",
                    extra={"error": str(e)}
                )
        
        return resolved_paths


# Global API client instance
kavita_api = KavitaAPIClient()

