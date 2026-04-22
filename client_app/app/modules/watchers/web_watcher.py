"""
WebWatcher Module - Web Page Change Detection

Monitors web pages for changes using content hashing.
Supports CSS and XPath selectors, screenshot capture, and workflow triggers.
Now includes diff generation to show exactly what changed.
"""
import hashlib
import asyncio
import difflib
from typing import Optional, Tuple, NamedTuple
from pathlib import Path
from datetime import datetime
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout


class CheckResult(NamedTuple):
    """Result of a URL check including content for diff generation."""
    changed: bool
    new_hash: str
    screenshot_path: Optional[str]
    content_text: Optional[str]  # Extracted text content
    content_html: Optional[str]  # Extracted HTML content


async def check_url_changes(
    page: Page,
    url: str,
    selector: str,
    selector_type: str,
    last_hash: Optional[str],
    capture_screenshot: bool = True,
    screenshot_dir: Optional[Path] = None,
    watch_mode: str = "selector",
    capture_content: bool = False
) -> CheckResult:
    """
    Check if URL content has changed.

    Args:
        page: Playwright page instance
        url: URL to check
        selector: CSS or XPath selector
        selector_type: 'css' or 'xpath'
        last_hash: Previous content hash (None for first check)
        capture_screenshot: Whether to capture screenshot
        screenshot_dir: Directory to save screenshots
        watch_mode: 'full_page' for smart digest or 'selector' for specific element
        capture_content: Whether to capture text/HTML content for diff generation

    Returns:
        CheckResult with (changed, new_hash, screenshot_path, content_text, content_html)

    Raises:
        Exception: On navigation or selector errors
    """
    try:
        # Navigate to URL with timeout
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Extract content based on watch mode
        content_text = None
        content_html = None

        if watch_mode == "full_page":
            content = await extract_content_smart(page)
            if capture_content:
                content_text = content
                content_html = await extract_html_smart(page)
        else:
            content = await extract_content(page, selector, selector_type)
            if capture_content:
                content_text = content
                content_html = await extract_html(page, selector, selector_type)

        # Calculate hash
        new_hash = calculate_hash(content)

        # Check if changed
        changed = last_hash is not None and new_hash != last_hash

        # Capture screenshot if requested and changed
        screenshot_path = None
        if capture_screenshot and (changed or last_hash is None):
            if screenshot_dir:
                screenshot_path = await capture_page_screenshot(page, url, screenshot_dir)

        return CheckResult(
            changed=changed,
            new_hash=new_hash,
            screenshot_path=screenshot_path,
            content_text=content_text,
            content_html=content_html
        )

    except PlaywrightTimeout:
        raise Exception(f"Timeout loading {url}")
    except Exception as e:
        raise Exception(f"Error checking {url}: {str(e)}")


async def extract_content(page: Page, selector: str, selector_type: str) -> str:
    """
    Extract content from page using selector.
    
    Args:
        page: Playwright page instance
        selector: CSS or XPath selector
        selector_type: 'css' or 'xpath'
    
    Returns:
        Extracted text content
    
    Raises:
        Exception: If selector is invalid or element not found
    """
    try:
        if selector_type == "css":
            # CSS selector
            element = await page.query_selector(selector)
            if not element:
                raise Exception(f"CSS selector '{selector}' not found")
            
            # Get text content
            content = await element.text_content()
            
        elif selector_type == "xpath":
            # XPath selector
            elements = await page.query_selector_all(f"xpath={selector}")
            if not elements:
                raise Exception(f"XPath selector '{selector}' not found")
            
            # Get text from first matching element
            content = await elements[0].text_content()
            
        else:
            raise Exception(f"Invalid selector_type: {selector_type}")
        
        # Return content or empty string
        return content.strip() if content else ""

    except Exception as e:
        raise Exception(f"Error extracting content: {str(e)}")


async def extract_content_smart(page: Page) -> str:
    """
    Extract clean content for full page mode (Smart Digest).

    Removes dynamic elements like scripts, styles, navigation, footers,
    cookie banners, and ads to focus on main content changes.

    Args:
        page: Playwright page instance

    Returns:
        Normalized text content from the main area
    """
    try:
        # Remove dynamic elements that cause false positives
        await page.evaluate('''
            () => {
                const selectorsToRemove = [
                    'script', 'style', 'noscript', 'iframe',
                    'nav', 'footer', 'header', 'aside',
                    '[class*="cookie"]', '[id*="cookie"]',
                    '[class*="banner"]', '[class*="popup"]',
                    '[class*="modal"]', '[class*="overlay"]',
                    '[class*="ad-"]', '[class*="ads-"]', '[class*="advertisement"]',
                    '[id*="ad-"]', '[id*="ads-"]',
                    '[class*="social"]', '[class*="share"]',
                    '[class*="newsletter"]', '[class*="subscribe"]',
                    '[role="banner"]', '[role="navigation"]', '[role="contentinfo"]'
                ];
                selectorsToRemove.forEach(selector => {
                    try {
                        document.querySelectorAll(selector).forEach(el => el.remove());
                    } catch(e) {}
                });
            }
        ''')

        # Try to find main content area
        main_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.content',
            '#content',
            '.main-content',
            '#main-content',
            '.post-content',
            '.article-content',
            '.entry-content'
        ]

        content = None
        for selector in main_selectors:
            element = await page.query_selector(selector)
            if element:
                content = await element.text_content()
                if content and len(content.strip()) > 50:
                    break

        # Fallback to body if no main content found
        if not content or len(content.strip()) < 50:
            body = await page.query_selector('body')
            content = await body.text_content() if body else ""

        # Normalize whitespace
        normalized = ' '.join(content.split()) if content else ""
        return normalized

    except Exception as e:
        raise Exception(f"Error extracting smart content: {str(e)}")


def calculate_hash(content: str) -> str:
    """
    Calculate SHA256 hash of content.
    
    Args:
        content: Text content to hash
    
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


async def capture_page_screenshot(
    page: Page,
    url: str,
    screenshot_dir: Path
) -> str:
    """
    Capture screenshot and return path.

    Args:
        page: Playwright page instance
        url: URL being captured (for filename)
        screenshot_dir: Directory to save screenshot

    Returns:
        Relative path to screenshot

    Raises:
        Exception: On screenshot capture failure
    """
    try:
        # Create directory if not exists
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        # Sanitize URL for filename
        url_safe = url.replace("https://", "").replace("http://", "")
        url_safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in url_safe)
        url_safe = url_safe[:50]  # Limit length
        
        filename = f"{url_safe}_{timestamp}.png"
        filepath = screenshot_dir / filename
        
        # Capture screenshot
        await page.screenshot(path=str(filepath), full_page=True)
        
        # Return relative path
        return str(filepath)
        
    except Exception as e:
        raise Exception(f"Error capturing screenshot: {str(e)}")


async def validate_selector(
    page: Page,
    url: str,
    selector: str,
    selector_type: str
) -> Tuple[bool, str]:
    """
    Validate that selector works on the given URL.
    
    Args:
        page: Playwright page instance
        url: URL to test
        selector: CSS or XPath selector
        selector_type: 'css' or 'xpath'
    
    Returns:
        (valid: bool, message: str)
    """
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        content = await extract_content(page, selector, selector_type)
        
        if not content:
            return False, f"Selector '{selector}' found but returned empty content"
        
        return True, f"Selector valid. Extracted {len(content)} characters"
        
    except PlaywrightTimeout:
        return False, f"Timeout loading {url}"
    except Exception as e:
        return False, str(e)


async def extract_html(page: Page, selector: str, selector_type: str) -> str:
    """
    Extract HTML content from page using selector.

    Args:
        page: Playwright page instance
        selector: CSS or XPath selector
        selector_type: 'css' or 'xpath'

    Returns:
        Extracted HTML content
    """
    try:
        if selector_type == "css":
            element = await page.query_selector(selector)
            if not element:
                return ""
            html = await element.inner_html()
        elif selector_type == "xpath":
            elements = await page.query_selector_all(f"xpath={selector}")
            if not elements:
                return ""
            html = await elements[0].inner_html()
        else:
            return ""

        return html.strip() if html else ""
    except Exception:
        return ""


async def extract_html_smart(page: Page) -> str:
    """
    Extract HTML content for full page mode.
    Tries to find main content area, falls back to body.

    Args:
        page: Playwright page instance

    Returns:
        HTML content from main area
    """
    try:
        main_selectors = [
            'main', 'article', '[role="main"]',
            '.content', '#content', '.main-content'
        ]

        for selector in main_selectors:
            element = await page.query_selector(selector)
            if element:
                html = await element.inner_html()
                if html and len(html.strip()) > 100:
                    return html.strip()

        # Fallback to body
        body = await page.query_selector('body')
        if body:
            return (await body.inner_html()).strip()
        return ""
    except Exception:
        return ""


# ============================================================================
# DIFF GENERATION FUNCTIONS
# ============================================================================

def generate_text_diff(old_text: str, new_text: str, context_lines: int = 3) -> str:
    """
    Generate a text diff showing changes between old and new content.
    Uses unified diff format with +/- prefixes.

    Args:
        old_text: Previous content
        new_text: New content
        context_lines: Number of context lines around changes

    Returns:
        Diff string with + for additions, - for deletions
    """
    if not old_text:
        old_text = ""
    if not new_text:
        new_text = ""

    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile='anterior',
        tofile='actual',
        n=context_lines
    )

    return ''.join(diff)


def generate_html_diff(old_text: str, new_text: str, max_lines: int = 100) -> str:
    """
    Generate an HTML-formatted diff with colored lines.
    Green for additions, red for deletions, gray for context.

    Args:
        old_text: Previous content
        new_text: New content
        max_lines: Maximum lines to include in diff

    Returns:
        HTML string with styled diff
    """
    if not old_text:
        old_text = ""
    if not new_text:
        new_text = ""

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    # Use ndiff for character-level comparison
    diff = list(difflib.ndiff(old_lines, new_lines))

    html_lines = []
    line_count = 0

    for line in diff:
        if line_count >= max_lines:
            html_lines.append(
                '<div style="color: #666; font-style: italic; padding: 4px;">... (más cambios omitidos)</div>'
            )
            break

        # Escape HTML entities
        escaped_line = (
            line[2:] if len(line) > 2 else ""
        ).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        if line.startswith('+ '):
            # Added line - green
            html_lines.append(
                f'<div style="color: #2e7d32; background-color: #e8f5e9; '
                f'padding: 2px 8px; margin: 1px 0; font-family: monospace; '
                f'border-left: 3px solid #4caf50;">+ {escaped_line}</div>'
            )
            line_count += 1
        elif line.startswith('- '):
            # Removed line - red
            html_lines.append(
                f'<div style="color: #c62828; background-color: #ffebee; '
                f'padding: 2px 8px; margin: 1px 0; font-family: monospace; '
                f'border-left: 3px solid #ef5350;">- {escaped_line}</div>'
            )
            line_count += 1
        elif line.startswith('  '):
            # Context line - gray (show fewer context lines)
            if line_count < 10 or any(l.startswith(('+', '-')) for l in diff[max(0, diff.index(line)-2):diff.index(line)+3]):
                html_lines.append(
                    f'<div style="color: #757575; padding: 2px 8px; margin: 1px 0; '
                    f'font-family: monospace;">&nbsp; {escaped_line}</div>'
                )
                line_count += 1
        # Skip '?' lines (character-level diff markers)

    if not html_lines:
        return '<div style="color: #666; font-style: italic;">Sin diferencias detectables en texto</div>'

    return ''.join(html_lines)


def generate_summary_diff(old_text: str, new_text: str) -> dict:
    """
    Generate a summary of changes with statistics.

    Args:
        old_text: Previous content
        new_text: New content

    Returns:
        Dictionary with lines_added, lines_removed, lines_changed
    """
    if not old_text:
        old_text = ""
    if not new_text:
        new_text = ""

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff = list(difflib.ndiff(old_lines, new_lines))

    added = sum(1 for line in diff if line.startswith('+ '))
    removed = sum(1 for line in diff if line.startswith('- '))

    return {
        "lines_added": added,
        "lines_removed": removed,
        "total_changes": added + removed,
        "old_line_count": len(old_lines),
        "new_line_count": len(new_lines)
    }
