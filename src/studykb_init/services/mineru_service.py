"""MinerU API service for converting documents to Markdown."""

import asyncio
import time
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

import httpx

from studykb_init.config import MineruConfig


class TaskState(Enum):
    """MinerU task states."""

    PENDING = "pending"
    WAITING = "waiting-file"
    RUNNING = "running"
    CONVERTING = "converting"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ConversionResult:
    """Result of a document conversion."""

    success: bool
    source_path: str
    output_path: str | None = None
    error: str | None = None


SUPPORTED_FORMATS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".html"}


class MineruService:
    """Service for converting documents to Markdown using MinerU API."""

    def __init__(self, config: MineruConfig):
        """Initialize the service.

        Args:
            config: MinerU API configuration.
        """
        self.config = config
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_token}",
        }

    @staticmethod
    def is_supported(file_path: str | Path) -> bool:
        """Check if a file format is supported.

        Args:
            file_path: Path to the file.

        Returns:
            True if the format is supported.
        """
        return Path(file_path).suffix.lower() in SUPPORTED_FORMATS

    async def convert_file(
        self,
        source_path: str | Path,
        output_dir: str | Path,
        on_progress: Callable[[str], None] | None = None,
    ) -> ConversionResult:
        """Convert a single file to Markdown.

        Args:
            source_path: Path to the source file.
            output_dir: Directory to save the output.
            on_progress: Optional callback for progress updates.

        Returns:
            ConversionResult with success status and output path.
        """
        source_path = Path(source_path)
        output_dir = Path(output_dir)

        if not source_path.exists():
            return ConversionResult(
                success=False,
                source_path=str(source_path),
                error=f"文件不存在: {source_path}",
            )

        if not self.is_supported(source_path):
            return ConversionResult(
                success=False,
                source_path=str(source_path),
                error=f"不支持的格式: {source_path.suffix}",
            )

        def report(msg: str) -> None:
            if on_progress:
                on_progress(msg)

        try:
            # 1. Request upload URL
            report("申请上传链接...")
            batch_id, upload_url = await self._request_upload_url(source_path.name)

            # 2. Upload file
            report("上传文件...")
            await self._upload_file(source_path, upload_url)

            # 3. Poll for completion
            report("等待解析...")
            download_url = await self._poll_status(batch_id, source_path.name, report)

            if not download_url:
                return ConversionResult(
                    success=False,
                    source_path=str(source_path),
                    error="解析超时或失败",
                )

            # 4. Download and extract result
            report("下载结果...")
            output_path = await self._download_result(
                download_url, source_path.stem, output_dir
            )

            report("完成!")
            return ConversionResult(
                success=True,
                source_path=str(source_path),
                output_path=str(output_path),
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                source_path=str(source_path),
                error=str(e),
            )

    async def _request_upload_url(self, file_name: str) -> tuple[str, str]:
        """Request upload URL from MinerU API.

        Args:
            file_name: Name of the file to upload.

        Returns:
            Tuple of (batch_id, upload_url).
        """
        url = f"{self.config.api_base}/file-urls/batch"
        data = {
            "files": [{"name": file_name}],
            "model_version": self.config.model_version,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=data, timeout=30)
            result = response.json()

        if result.get("code") != 0:
            raise Exception(f"申请上传链接失败: {result.get('msg', '未知错误')}")

        batch_id = result["data"]["batch_id"]
        upload_url = result["data"]["file_urls"][0]
        return batch_id, upload_url

    async def _upload_file(self, file_path: Path, upload_url: str) -> None:
        """Upload file to the provided URL.

        Args:
            file_path: Path to the file.
            upload_url: Pre-signed upload URL.
        """
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                response = await client.put(upload_url, content=f.read(), timeout=120)

            if response.status_code != 200:
                raise Exception(f"上传失败: HTTP {response.status_code}")

    async def _poll_status(
        self,
        batch_id: str,
        file_name: str,
        on_progress: Callable[[str], None],
    ) -> str | None:
        """Poll for task completion.

        Args:
            batch_id: Batch ID from upload request.
            file_name: Name of the file being processed.
            on_progress: Progress callback.

        Returns:
            Download URL if successful, None if failed/timeout.
        """
        url = f"{self.config.api_base}/extract-results/batch/{batch_id}"
        start_time = time.time()

        while time.time() - start_time < self.config.max_poll_time:
            await asyncio.sleep(self.config.poll_interval)

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30)
                result = response.json()

            if result.get("code") != 0:
                continue

            extract_results = result.get("data", {}).get("extract_result", [])

            for item in extract_results:
                if item.get("file_name") != file_name:
                    continue

                state = item.get("state", "")

                if state == "done":
                    return item.get("full_zip_url", "")

                elif state == "failed":
                    err_msg = item.get("err_msg", "解析失败")
                    raise Exception(err_msg)

                elif state == "running":
                    progress = item.get("extract_progress", {})
                    extracted = progress.get("extracted_pages", 0)
                    total = progress.get("total_pages", 0)
                    if total > 0:
                        on_progress(f"解析中 {extracted}/{total} 页")
                    else:
                        on_progress("解析中...")

                elif state == "converting":
                    on_progress("格式转换中...")

                elif state == "pending":
                    on_progress("排队中...")

        return None

    async def _download_result(
        self,
        download_url: str,
        file_stem: str,
        output_dir: Path,
    ) -> Path:
        """Download and extract conversion result.

        Args:
            download_url: URL to download the result ZIP.
            file_stem: Original file name without extension.
            output_dir: Directory to save output.

        Returns:
            Path to the extracted Markdown file.
        """
        import shutil

        output_dir.mkdir(parents=True, exist_ok=True)

        # Download ZIP
        async with httpx.AsyncClient() as client:
            response = await client.get(download_url, timeout=120)

        zip_path = output_dir / f"{file_stem}_result.zip"
        with open(zip_path, "wb") as f:
            f.write(response.content)

        # Extract
        extract_dir = output_dir / f"{file_stem}_extracted"
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Find the main markdown file
        md_files = list(extract_dir.rglob("*.md"))
        if not md_files:
            raise Exception("未找到 Markdown 文件")

        # Use the largest MD file (usually the main content)
        main_md = max(md_files, key=lambda p: p.stat().st_size)

        # Copy MD to output with clean name
        final_path = output_dir / f"{file_stem}.md"
        final_path.write_text(main_md.read_text(encoding="utf-8"), encoding="utf-8")

        # Copy images folder if exists (check in same directory as main_md and in extract root)
        images_dir = output_dir / "images"

        # Look for images folder in multiple locations
        possible_image_dirs = [
            main_md.parent / "images",
            extract_dir / "images",
        ]

        # Also check for any images folder in the extracted content
        for img_dir in extract_dir.rglob("images"):
            if img_dir.is_dir():
                possible_image_dirs.append(img_dir)

        for src_images in possible_image_dirs:
            if src_images.exists() and src_images.is_dir():
                # If images dir already exists, merge contents
                if images_dir.exists():
                    for img_file in src_images.iterdir():
                        if img_file.is_file():
                            dest = images_dir / img_file.name
                            if not dest.exists():
                                shutil.copy2(img_file, dest)
                else:
                    shutil.copytree(src_images, images_dir)
                break  # Only copy from first found images dir

        # Cleanup
        zip_path.unlink()
        shutil.rmtree(extract_dir)

        return final_path
