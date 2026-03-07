#!/usr/bin/env python3
"""
Payer Policy Download Pipeline — Anti-VEGF Prior Authorization Rule Library

Downloads publicly available medical policy documents, coverage criteria,
formularies, and PA requirement lists from 6 major payers for anti-VEGF
intravitreal injection prior authorization.

Usage:
    python download_policies.py                       # Download all payers
    python download_policies.py --payer cms_medicare   # Download one payer
    python download_policies.py --payer uhc aetna      # Download specific payers
    python download_policies.py --list                 # List configured payers
    python download_policies.py --verify               # Verify existing downloads
    python download_policies.py --playwright           # Use Playwright for JS pages
"""

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("policy_downloader")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DownloadRecord:
    """Tracks a single downloaded file."""
    payer_id: str
    payer_name: str
    document_type: str
    filename: str
    source_url: str
    download_timestamp: str
    file_size_bytes: int
    sha256: str
    content_type: str
    description: str
    status: str  # "success", "failed", "skipped", "stub"
    error: Optional[str] = None


@dataclass
class Manifest:
    """Tracks all downloads across all payers."""
    generated_at: str = ""
    total_files: int = 0
    total_bytes: int = 0
    payers_attempted: list = field(default_factory=list)
    payers_succeeded: list = field(default_factory=list)
    downloads: list = field(default_factory=list)

    def add(self, record: DownloadRecord):
        self.downloads.append(asdict(record))
        if record.status == "success":
            self.total_files += 1
            self.total_bytes += record.file_size_bytes

    def save(self, path: Path):
        self.generated_at = datetime.now(timezone.utc).isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
        log.info(f"Manifest saved: {path} ({self.total_files} files, {self.total_bytes:,} bytes)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name)
    return name[:200].strip('_')


def is_stub(path: Path, settings: dict) -> bool:
    """
    Detect if a downloaded file is a redirect stub rather than real content.

    WORKAROUND: Many payer CDNs (Aetna, BCBSTX) return small JavaScript
    redirect pages instead of the actual content when:
      - The User-Agent is not browser-like
      - The page requires JS rendering
      - The URL has been restructured (soft 404)

    These stubs are typically <2KB and contain redirect scripts.
    Real PDFs are >5KB; real HTML policy pages are >2KB.
    """
    size = path.stat().st_size
    suffix = path.suffix.lower()

    min_pdf = settings.get("min_pdf_bytes", 5000)
    min_html = settings.get("min_html_bytes", 2000)

    if suffix == ".pdf" and size < min_pdf:
        return True
    if suffix in (".html", ".htm") and size < min_html:
        return True
    return False


def download_file(url: str, dest: Path, session: requests.Session,
                  delay: float = 2.0, timeout: int = 30,
                  settings: dict = None) -> tuple[bool, str, int, str]:
    """
    Download a file from url to dest.
    Returns (success, content_type, file_size, error_message).
    Detects redirect stubs and flags them as failures.
    """
    try:
        time.sleep(delay)
        resp = session.get(url, timeout=timeout, stream=True, allow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "unknown")
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = dest.stat().st_size

        # Check for redirect stubs
        if settings and is_stub(dest, settings):
            dest.unlink()
            return False, content_type, file_size, (
                f"Stub detected ({file_size} bytes) — file is a JS redirect, "
                f"not real content. Use --playwright mode or check URL."
            )

        return True, content_type, file_size, ""

    except requests.exceptions.HTTPError as e:
        return False, "", 0, f"HTTP {e.response.status_code}: {e}"
    except requests.exceptions.ConnectionError as e:
        return False, "", 0, f"Connection error: {e}"
    except requests.exceptions.Timeout:
        return False, "", 0, f"Timeout after {timeout}s"
    except Exception as e:
        return False, "", 0, str(e)


def download_page(url: str, session: requests.Session,
                  delay: float = 2.0, timeout: int = 30) -> tuple[Optional[str], str]:
    """
    Download an HTML page and return (html_content, error_message).
    """
    try:
        time.sleep(delay)
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text, ""
    except Exception as e:
        return None, str(e)


def find_pdf_links(html: str, base_url: str, keywords: list[str]) -> list[tuple[str, str]]:
    """
    Parse HTML and find PDF links matching keywords.
    Returns list of (url, link_text) tuples.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        combined = f"{href} {text}".lower()

        is_pdf = href.lower().endswith(".pdf") or "pdf" in combined
        matches_keyword = any(kw.lower() in combined for kw in keywords)

        if is_pdf and matches_keyword:
            full_url = urljoin(base_url, href)
            results.append((full_url, text))

    return results


def save_page_as_html(html: str, dest: Path, url: str):
    """Save an HTML page with a source header."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(f"<!-- Source: {url} -->\n")
        f.write(f"<!-- Downloaded: {datetime.now(timezone.utc).isoformat()} -->\n\n")
        f.write(html)


# ---------------------------------------------------------------------------
# Direct PDF downloader
# ---------------------------------------------------------------------------

def download_direct_pdfs(payer_id: str, config: dict, session: requests.Session,
                         manifest: Manifest, base_dir: Path, settings: dict):
    """
    Download PDFs from known direct URLs listed in config.

    WORKAROUND: Many payer sites are JS-rendered, so their HTML pages
    don't contain PDF links visible to requests/BeautifulSoup. However,
    the actual PDF URLs are stable and can be downloaded directly once
    discovered (via Playwright browsing, payer documentation, etc.).

    This function downloads PDFs listed under the 'direct_pdfs' key
    in each payer's config. These URLs were discovered during initial
    Playwright exploration and are known to return real content with
    a browser-like User-Agent.
    """
    payer_name = config["name"]
    payer_dir = base_dir / payer_id
    payer_dir.mkdir(parents=True, exist_ok=True)
    delay = settings["request_delay_seconds"]
    timeout = settings["timeout_seconds"]

    direct_pdfs = config.get("direct_pdfs", [])
    if not direct_pdfs:
        return

    log.info(f"  Downloading {len(direct_pdfs)} direct PDF(s)...")

    for pdf_entry in direct_pdfs:
        url = pdf_entry["url"]
        filename = pdf_entry["filename"]
        description = pdf_entry["description"]
        dest = payer_dir / filename

        if dest.exists() and dest.stat().st_size > settings.get("min_pdf_bytes", 5000):
            log.info(f"    Already exists: {filename} ({dest.stat().st_size:,} bytes)")
            manifest.add(DownloadRecord(
                payer_id=payer_id, payer_name=payer_name,
                document_type="direct_pdf", filename=str(dest.relative_to(base_dir)),
                source_url=url, download_timestamp=datetime.now(timezone.utc).isoformat(),
                file_size_bytes=dest.stat().st_size, sha256=sha256_file(dest),
                content_type="application/pdf", description=description,
                status="success"
            ))
            continue

        log.info(f"    Downloading: {filename}")
        ok, ct, size, err = download_file(url, dest, session, delay, timeout, settings)
        manifest.add(DownloadRecord(
            payer_id=payer_id, payer_name=payer_name,
            document_type="direct_pdf", filename=str(dest.relative_to(base_dir)) if ok else "",
            source_url=url, download_timestamp=datetime.now(timezone.utc).isoformat(),
            file_size_bytes=size, sha256=sha256_file(dest) if ok else "",
            content_type=ct, description=description,
            status="success" if ok else "failed", error=err or None
        ))
        if ok:
            log.info(f"      OK: {size:,} bytes")
        else:
            log.warning(f"      FAILED: {err}")


# ---------------------------------------------------------------------------
# Playwright downloader (for JS-rendered pages)
# ---------------------------------------------------------------------------

def download_with_playwright(url: str, dest: Path, timeout_ms: int = 30000) -> tuple[bool, str]:
    """
    Use Playwright to download a JS-rendered page.

    WORKAROUND: Aetna CPBs, BCBSTX medical policies, Humana coverage
    pages, and Cigna/EviCore guidelines all require JavaScript execution
    to render their content. Plain requests returns either:
      - A ~1KB redirect/loader stub
      - A 404 error (when the server rejects non-browser clients)

    Playwright renders the full page and saves the complete HTML.

    Requires: pip install playwright && playwright install chromium
    """
    try:
        script = f"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("{url}", wait_until="networkidle", timeout={timeout_ms})
        html = await page.content()
        with open("{dest}", "w") as f:
            f.write(html)
        await browser.close()
        print(f"OK: {{len(html)}} chars")

asyncio.run(main())
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and dest.exists():
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Playwright timed out after 60s"
    except Exception as e:
        return False, str(e)


def download_playwright_urls(payer_id: str, config: dict,
                             manifest: Manifest, base_dir: Path):
    """Download JS-rendered pages listed under playwright_urls in config."""
    payer_name = config["name"]
    payer_dir = base_dir / payer_id
    payer_dir.mkdir(parents=True, exist_ok=True)

    pw_urls = config.get("playwright_urls", [])
    if not pw_urls:
        return

    log.info(f"  Downloading {len(pw_urls)} Playwright-rendered page(s)...")

    for entry in pw_urls:
        url = entry["url"]
        filename = entry["filename"]
        description = entry["description"]
        dest = payer_dir / filename

        log.info(f"    Playwright: {filename}")
        ok, msg = download_with_playwright(url, dest)
        manifest.add(DownloadRecord(
            payer_id=payer_id, payer_name=payer_name,
            document_type="playwright_page", filename=str(dest.relative_to(base_dir)) if ok else "",
            source_url=url, download_timestamp=datetime.now(timezone.utc).isoformat(),
            file_size_bytes=dest.stat().st_size if ok else 0,
            sha256=sha256_file(dest) if ok else "",
            content_type="text/html", description=description,
            status="success" if ok else "failed", error=None if ok else msg
        ))
        if ok:
            log.info(f"      OK: {msg}")
        else:
            log.warning(f"      FAILED: {msg}")


def download_source_with_playwright(url: str, payer_id: str, payer_name: str,
                                    doc_type: str, description: str,
                                    manifest: Manifest, base_dir: Path):
    """Download a single source URL using Playwright (fallback for needs_playwright sources)."""
    payer_dir = base_dir / payer_id
    payer_dir.mkdir(parents=True, exist_ok=True)
    fname = safe_filename(f"{doc_type}_{description}") + ".html"
    dest = payer_dir / fname

    log.info(f"    Playwright fallback: {fname}")
    ok, msg = download_with_playwright(url, dest)
    manifest.add(DownloadRecord(
        payer_id=payer_id, payer_name=payer_name,
        document_type=doc_type, filename=str(dest.relative_to(base_dir)) if ok else "",
        source_url=url, download_timestamp=datetime.now(timezone.utc).isoformat(),
        file_size_bytes=dest.stat().st_size if ok else 0,
        sha256=sha256_file(dest) if ok else "",
        content_type="text/html", description=description,
        status="success" if ok else "failed", error=None if ok else msg
    ))
    if ok:
        log.info(f"      OK: {msg}")
    else:
        log.warning(f"      FAILED: {msg}")


# ---------------------------------------------------------------------------
# Payer-specific downloaders
# ---------------------------------------------------------------------------

def download_cms_medicare(config: dict, session: requests.Session,
                          manifest: Manifest, base_dir: Path, settings: dict,
                          use_playwright: bool = False):
    """Download CMS Medicare Traditional policy documents."""
    payer_id = "cms_medicare"
    payer_name = config["name"]
    payer_dir = base_dir / payer_id
    payer_dir.mkdir(parents=True, exist_ok=True)
    delay = settings["request_delay_seconds"]
    timeout = settings["timeout_seconds"]

    log.info(f"=== {payer_name} ===")

    # 1. Download LCD L33346 page
    log.info("Downloading LCD L33346 (Intravitreal Injections — Novitas)...")
    lcd_url = "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33346"
    html, err = download_page(lcd_url, session, delay, timeout)
    if html:
        dest = payer_dir / "LCD_L33346_intravitreal_injections.html"
        save_page_as_html(html, dest, lcd_url)
        manifest.add(DownloadRecord(
            payer_id=payer_id, payer_name=payer_name,
            document_type="lcd", filename=str(dest.relative_to(base_dir)),
            source_url=lcd_url, download_timestamp=datetime.now(timezone.utc).isoformat(),
            file_size_bytes=dest.stat().st_size, sha256=sha256_file(dest),
            content_type="text/html", description="LCD L33346 — Intravitreal Injections (Novitas, JH)",
            status="success"
        ))

        # Find PDF links within the LCD page
        pdf_links = find_pdf_links(html, lcd_url, ["lcd", "intravitreal", "injection", "article"])
        for pdf_url, link_text in pdf_links[:5]:
            fname = safe_filename(link_text or urlparse(pdf_url).path.split("/")[-1]) + ".pdf"
            dest_pdf = payer_dir / fname
            log.info(f"  Downloading linked PDF: {fname}")
            ok, ct, size, err = download_file(pdf_url, dest_pdf, session, delay, timeout, settings)
            manifest.add(DownloadRecord(
                payer_id=payer_id, payer_name=payer_name,
                document_type="lcd_attachment", filename=str(dest_pdf.relative_to(base_dir)),
                source_url=pdf_url, download_timestamp=datetime.now(timezone.utc).isoformat(),
                file_size_bytes=size, sha256=sha256_file(dest_pdf) if ok else "",
                content_type=ct, description=f"LCD attachment: {link_text}",
                status="success" if ok else "failed", error=err or None
            ))
    else:
        log.warning(f"  Failed to download LCD page: {err}")
        manifest.add(DownloadRecord(
            payer_id=payer_id, payer_name=payer_name,
            document_type="lcd", filename="",
            source_url=lcd_url, download_timestamp=datetime.now(timezone.utc).isoformat(),
            file_size_bytes=0, sha256="", content_type="",
            description="LCD L33346", status="failed", error=err
        ))

    # 2. Search CMS Medicare Coverage Database
    log.info("Searching CMS Medicare Coverage Database...")
    search_terms = ["intravitreal+injection", "anti-VEGF", "aflibercept", "bevacizumab"]
    for term in search_terms:
        search_url = f"https://www.cms.gov/medicare-coverage-database/search.aspx?q={term}"
        html, err = download_page(search_url, session, delay, timeout)
        if html:
            dest = payer_dir / f"search_results_{safe_filename(term)}.html"
            save_page_as_html(html, dest, search_url)
            manifest.add(DownloadRecord(
                payer_id=payer_id, payer_name=payer_name,
                document_type="search_results", filename=str(dest.relative_to(base_dir)),
                source_url=search_url, download_timestamp=datetime.now(timezone.utc).isoformat(),
                file_size_bytes=dest.stat().st_size, sha256=sha256_file(dest),
                content_type="text/html", description=f"Coverage DB search: {term}",
                status="success"
            ))

            # Download any PDFs found in search results
            pdf_links = find_pdf_links(html, search_url,
                                       ["lcd", "ncd", "intravitreal", "ophthalmology",
                                        "injection", "VEGF", "aflibercept", "bevacizumab"])
            for pdf_url, link_text in pdf_links[:3]:
                fname = safe_filename(link_text or urlparse(pdf_url).path.split("/")[-1])
                if not fname.endswith(".pdf"):
                    fname += ".pdf"
                dest_pdf = payer_dir / fname
                if not dest_pdf.exists():
                    log.info(f"  Downloading: {fname}")
                    ok, ct, size, err2 = download_file(pdf_url, dest_pdf, session, delay, timeout, settings)
                    manifest.add(DownloadRecord(
                        payer_id=payer_id, payer_name=payer_name,
                        document_type="lcd_pdf", filename=str(dest_pdf.relative_to(base_dir)),
                        source_url=pdf_url, download_timestamp=datetime.now(timezone.utc).isoformat(),
                        file_size_bytes=size, sha256=sha256_file(dest_pdf) if ok else "",
                        content_type=ct, description=f"Search result PDF: {link_text}",
                        status="success" if ok else "failed", error=err2 or None
                    ))

    # 3. Download ASP pricing page
    log.info("Downloading ASP Drug Pricing page...")
    asp_url = "https://www.cms.gov/medicare/payment/part-b-drugs/average-sales-price"
    html, err = download_page(asp_url, session, delay, timeout)
    if html:
        dest = payer_dir / "asp_drug_pricing.html"
        save_page_as_html(html, dest, asp_url)
        manifest.add(DownloadRecord(
            payer_id=payer_id, payer_name=payer_name,
            document_type="asp_pricing", filename=str(dest.relative_to(base_dir)),
            source_url=asp_url, download_timestamp=datetime.now(timezone.utc).isoformat(),
            file_size_bytes=dest.stat().st_size, sha256=sha256_file(dest),
            content_type="text/html", description="Part B Drug ASP Pricing",
            status="success"
        ))

        # Find ASP pricing file downloads (Excel/CSV)
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if any(ext in href for ext in [".xlsx", ".csv", ".zip"]) and "asp" in href:
                full_url = urljoin(asp_url, a["href"])
                fname = urlparse(full_url).path.split("/")[-1]
                dest_file = payer_dir / fname
                if not dest_file.exists():
                    log.info(f"  Downloading ASP file: {fname}")
                    ok, ct, size, err2 = download_file(full_url, dest_file, session, delay, timeout, settings)
                    manifest.add(DownloadRecord(
                        payer_id=payer_id, payer_name=payer_name,
                        document_type="asp_data", filename=str(dest_file.relative_to(base_dir)),
                        source_url=full_url, download_timestamp=datetime.now(timezone.utc).isoformat(),
                        file_size_bytes=size, sha256=sha256_file(dest_file) if ok else "",
                        content_type=ct, description=f"ASP pricing data: {fname}",
                        status="success" if ok else "failed", error=err2 or None
                    ))


def download_payer_generic(payer_id: str, config: dict, session: requests.Session,
                           manifest: Manifest, base_dir: Path, settings: dict,
                           use_playwright: bool = False):
    """Generic downloader for MA payers — downloads source pages and linked PDFs."""
    payer_name = config["name"]
    payer_dir = base_dir / payer_id
    payer_dir.mkdir(parents=True, exist_ok=True)
    delay = settings["request_delay_seconds"]
    timeout = settings["timeout_seconds"]
    keywords = config.get("search_keywords", [])

    log.info(f"=== {payer_name} ===")

    # 1. Download direct PDFs first (most reliable)
    download_direct_pdfs(payer_id, config, session, manifest, base_dir, settings)

    # 2. Download source pages
    for source in config.get("sources", []):
        doc_type = source["type"]
        url = source["url"]
        description = source["description"]
        needs_pw = source.get("needs_playwright", False)

        log.info(f"  [{doc_type}] {description}")
        log.info(f"    URL: {url}")

        # Use Playwright for JS-rendered pages when --playwright is set
        if needs_pw and use_playwright:
            download_source_with_playwright(
                url, payer_id, payer_name, doc_type, description,
                manifest, base_dir
            )
            continue
        elif needs_pw and not use_playwright:
            log.warning(f"    SKIPPED: Needs Playwright (JS-rendered). Run with --playwright to download.")
            manifest.add(DownloadRecord(
                payer_id=payer_id, payer_name=payer_name,
                document_type=doc_type, filename="",
                source_url=url, download_timestamp=datetime.now(timezone.utc).isoformat(),
                file_size_bytes=0, sha256="", content_type="",
                description=description, status="skipped",
                error="Needs --playwright (JS-rendered page)"
            ))
            continue

        # Standard download
        html, err = download_page(url, session, delay, timeout)
        if not html:
            if use_playwright:
                log.warning(f"    requests failed ({err}), trying Playwright...")
                download_source_with_playwright(
                    url, payer_id, payer_name, doc_type, description,
                    manifest, base_dir
                )
            else:
                log.warning(f"    Failed: {err}")
                manifest.add(DownloadRecord(
                    payer_id=payer_id, payer_name=payer_name,
                    document_type=doc_type, filename="",
                    source_url=url, download_timestamp=datetime.now(timezone.utc).isoformat(),
                    file_size_bytes=0, sha256="", content_type="",
                    description=description, status="failed", error=err
                ))
            continue

        # Save the HTML page
        fname = safe_filename(f"{doc_type}_{description}") + ".html"
        dest = payer_dir / fname
        save_page_as_html(html, dest, url)

        # Check for HTML stubs
        if is_stub(dest, settings):
            log.warning(f"    Stub detected ({dest.stat().st_size} bytes) — page is JS-rendered")
            dest.unlink()
            if use_playwright:
                log.info(f"    Retrying with Playwright...")
                download_source_with_playwright(
                    url, payer_id, payer_name, doc_type, description,
                    manifest, base_dir
                )
            else:
                manifest.add(DownloadRecord(
                    payer_id=payer_id, payer_name=payer_name,
                    document_type=doc_type, filename="",
                    source_url=url, download_timestamp=datetime.now(timezone.utc).isoformat(),
                    file_size_bytes=0, sha256="", content_type="",
                    description=description, status="stub",
                    error="JS redirect stub — run with --playwright"
                ))
            continue

        manifest.add(DownloadRecord(
            payer_id=payer_id, payer_name=payer_name,
            document_type=doc_type, filename=str(dest.relative_to(base_dir)),
            source_url=url, download_timestamp=datetime.now(timezone.utc).isoformat(),
            file_size_bytes=dest.stat().st_size, sha256=sha256_file(dest),
            content_type="text/html", description=description,
            status="success"
        ))

        # Find and download linked PDFs matching our keywords
        pdf_links = find_pdf_links(html, url, keywords + [
            "intravitreal", "anti-VEGF", "VEGF", "ophthalmology", "retina",
            "injection", "aflibercept", "bevacizumab", "ranibizumab",
            "faricimab", "prior auth", "formulary", "step therapy",
            "67028", "J0178", "J9035"
        ])

        if pdf_links:
            log.info(f"    Found {len(pdf_links)} relevant PDF links")
            for pdf_url, link_text in pdf_links[:10]:
                pdf_fname = safe_filename(link_text or urlparse(pdf_url).path.split("/")[-1])
                if not pdf_fname.endswith(".pdf"):
                    pdf_fname += ".pdf"
                dest_pdf = payer_dir / pdf_fname
                if dest_pdf.exists():
                    log.info(f"    Already exists: {pdf_fname}")
                    continue
                log.info(f"    Downloading: {pdf_fname}")
                ok, ct, size, err2 = download_file(pdf_url, dest_pdf, session, delay, timeout, settings)
                manifest.add(DownloadRecord(
                    payer_id=payer_id, payer_name=payer_name,
                    document_type=f"{doc_type}_pdf", filename=str(dest_pdf.relative_to(base_dir)),
                    source_url=pdf_url, download_timestamp=datetime.now(timezone.utc).isoformat(),
                    file_size_bytes=size, sha256=sha256_file(dest_pdf) if ok else "",
                    content_type=ct, description=f"{description}: {link_text}",
                    status="success" if ok else "failed", error=err2 or None
                ))
        else:
            log.info("    No matching PDF links found (may need --playwright for JS-rendered content)")

    # 3. Download Playwright-rendered pages if enabled
    if use_playwright:
        download_playwright_urls(payer_id, config, manifest, base_dir)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_downloads(base_dir: Path, manifest_path: Path):
    """Verify integrity of all downloaded files against the manifest."""
    if not manifest_path.exists():
        log.error(f"Manifest not found: {manifest_path}")
        return False

    with open(manifest_path) as f:
        manifest_data = json.load(f)

    downloads = manifest_data.get("downloads", [])
    total = len([d for d in downloads if d["status"] == "success"])
    passed = 0
    failed = 0
    stubs = len([d for d in downloads if d["status"] == "stub"])
    skipped = len([d for d in downloads if d["status"] == "skipped"])

    log.info(f"Verifying {total} downloaded files...")

    for record in downloads:
        if record["status"] != "success":
            continue

        filepath = base_dir / record["filename"]
        if not filepath.exists():
            log.error(f"  MISSING: {record['filename']}")
            failed += 1
            continue

        actual_sha = sha256_file(filepath)
        if actual_sha != record["sha256"]:
            log.error(f"  CHECKSUM MISMATCH: {record['filename']}")
            log.error(f"    Expected: {record['sha256']}")
            log.error(f"    Actual:   {actual_sha}")
            failed += 1
            continue

        passed += 1

    log.info(f"\nVerification: {passed}/{total} PASSED, {failed} FAILED")
    if stubs:
        log.info(f"  {stubs} stub(s) detected — re-run with --playwright")
    if skipped:
        log.info(f"  {skipped} source(s) skipped — need --playwright")
    return failed == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Download payer policy documents for anti-VEGF PA rules")
    parser.add_argument("--payer", nargs="*", help="Specific payer(s) to download (default: all)")
    parser.add_argument("--list", action="store_true", help="List configured payers and exit")
    parser.add_argument("--verify", action="store_true", help="Verify existing downloads against manifest")
    parser.add_argument("--playwright", action="store_true",
                        help="Use Playwright for JS-rendered pages (requires: pip install playwright && playwright install chromium)")
    parser.add_argument("--config", default="config.yaml", help="Config file path (default: config.yaml)")
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        log.error(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    payers = config["payers"]
    settings = config["settings"]
    output = config["output"]
    base_dir = Path(output["base_dir"])
    manifest_path = Path(output["manifest_file"])

    # List mode
    if args.list:
        print("\nConfigured payers:")
        for pid, pconfig in payers.items():
            source_count = len(pconfig.get("sources", []))
            pdf_count = len(pconfig.get("direct_pdfs", []))
            pw_count = len(pconfig.get("playwright_urls", []))
            needs_pw = sum(1 for s in pconfig.get("sources", []) if s.get("needs_playwright"))
            extras = []
            if pdf_count:
                extras.append(f"{pdf_count} direct PDFs")
            if pw_count:
                extras.append(f"{pw_count} Playwright URLs")
            if needs_pw:
                extras.append(f"{needs_pw} need Playwright")
            extra_str = f"  [{', '.join(extras)}]" if extras else ""
            print(f"  {pid:20s}  {pconfig['name']:45s}  ({source_count} sources){extra_str}")
        print(f"\nTotal: {len(payers)} payers")
        if any(s.get("needs_playwright") for p in payers.values() for s in p.get("sources", [])):
            print("  Note: Some sources need --playwright for JS-rendered content")
        return

    # Verify mode
    if args.verify:
        ok = verify_downloads(base_dir, manifest_path)
        sys.exit(0 if ok else 1)

    # Playwright check
    if args.playwright:
        try:
            subprocess.run([sys.executable, "-c", "import playwright"], check=True,
                           capture_output=True)
        except subprocess.CalledProcessError:
            log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            sys.exit(1)

    # Download mode
    target_payers = args.payer if args.payer else list(payers.keys())
    invalid = [p for p in target_payers if p not in payers]
    if invalid:
        log.error(f"Unknown payer(s): {', '.join(invalid)}")
        log.error(f"Valid payers: {', '.join(payers.keys())}")
        sys.exit(1)

    # Create HTTP session with browser-like headers
    session = requests.Session()
    session.headers.update({
        "User-Agent": settings["user_agent"],
        "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })

    manifest = Manifest()
    manifest.payers_attempted = target_payers

    mode = "requests + Playwright" if args.playwright else "requests only"
    log.info(f"Starting policy download for {len(target_payers)} payer(s): {', '.join(target_payers)}")
    log.info(f"Mode: {mode}")
    log.info(f"Output directory: {base_dir.resolve()}")
    print()

    for payer_id in target_payers:
        payer_config = payers[payer_id]
        try:
            if payer_id == "cms_medicare":
                download_cms_medicare(payer_config, session, manifest, base_dir, settings, args.playwright)
            else:
                download_payer_generic(payer_id, payer_config, session, manifest, base_dir, settings, args.playwright)
            manifest.payers_succeeded.append(payer_id)
        except Exception as e:
            log.error(f"Error downloading {payer_id}: {e}")
        print()

    # Save manifest
    manifest.save(manifest_path)

    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    success = [d for d in manifest.downloads if d["status"] == "success"]
    failed = [d for d in manifest.downloads if d["status"] == "failed"]
    stubs = [d for d in manifest.downloads if d["status"] == "stub"]
    skipped = [d for d in manifest.downloads if d["status"] == "skipped"]
    print(f"  Payers attempted:  {len(manifest.payers_attempted)}")
    print(f"  Payers succeeded:  {len(manifest.payers_succeeded)}")
    print(f"  Files downloaded:  {len(success)}")
    print(f"  Files failed:      {len(failed)}")
    print(f"  Stubs detected:    {len(stubs)}")
    print(f"  Skipped (need PW): {len(skipped)}")
    print(f"  Total size:        {manifest.total_bytes:,} bytes ({manifest.total_bytes / 1024 / 1024:.1f} MB)")
    print(f"  Manifest:          {manifest_path}")

    if failed:
        print(f"\n  Failed downloads:")
        for d in failed:
            print(f"    - [{d['payer_id']}] {d['description']}: {d.get('error', 'unknown')}")

    if stubs:
        print(f"\n  Stub detections (re-run with --playwright):")
        for d in stubs:
            print(f"    - [{d['payer_id']}] {d['description']}")

    if skipped:
        print(f"\n  Skipped sources (need --playwright):")
        for d in skipped:
            print(f"    - [{d['payer_id']}] {d['description']}")

    # Per-payer breakdown
    print(f"\n  Per-payer breakdown:")
    for pid in manifest.payers_attempted:
        payer_files = [d for d in success if d["payer_id"] == pid]
        payer_bytes = sum(d["file_size_bytes"] for d in payer_files)
        payer_stubs = len([d for d in stubs if d["payer_id"] == pid])
        payer_skipped = len([d for d in skipped if d["payer_id"] == pid])
        status = "OK" if pid in manifest.payers_succeeded else "FAILED"
        notes = []
        if payer_stubs:
            notes.append(f"{payer_stubs} stubs")
        if payer_skipped:
            notes.append(f"{payer_skipped} skipped")
        note_str = f"  ({', '.join(notes)})" if notes else ""
        print(f"    {pid:20s}  {len(payer_files):3d} files  {payer_bytes:>10,} bytes  [{status}]{note_str}")

    print()

    # Verify
    log.info("Running post-download verification...")
    verify_downloads(base_dir, manifest_path)


if __name__ == "__main__":
    main()
