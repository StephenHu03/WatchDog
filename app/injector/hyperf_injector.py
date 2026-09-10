"""Hyperf-specific runtime injection for generated customer releases."""

from __future__ import annotations

import re
from pathlib import Path


class HyperfInjector:
    """Install a per-request guard because Hyperf's bootstrap runs in CLI."""

    middleware_class = r"\App\Middleware\LicenseProtectorMiddleware::class"

    def inject(self, project_root: Path) -> list[Path]:
        """Create and register a middleware before all customer HTTP middleware.

        The generated file belongs only to the delivery copy. It deliberately
        uses ``require`` instead of ``require_once`` so the Watchdog validates
        every request in a long-running Hyperf worker.
        """
        middleware = project_root / "app" / "Middleware" / "LicenseProtectorMiddleware.php"
        config = project_root / "config" / "autoload" / "middlewares.php"
        if not config.is_file():
            raise FileNotFoundError("Hyperf middleware configuration not found")

        middleware.parent.mkdir(parents=True, exist_ok=True)
        middleware.write_text(
            """<?php

declare(strict_types=1);

namespace App\\Middleware;

use Psr\\Http\\Message\\ResponseInterface;
use Psr\\Http\\Message\\ServerRequestInterface;
use Psr\\Http\\Server\\MiddlewareInterface;
use Psr\\Http\\Server\\RequestHandlerInterface;

/** Validates the signed license against the Host of every Hyperf request. */
final class LicenseProtectorMiddleware implements MiddlewareInterface
{
    public function process(ServerRequestInterface $request, RequestHandlerInterface $handler): ResponseInterface
    {
        // PHP includes inherit this method's scope, which safely supplies the
        // request Host without sharing state between Hyperf coroutines.
        $__lp_request_host = $request->getHeaderLine('Host');
        require dirname(__DIR__, 2) . '/protected/watchdog/loader.php';

        return $handler->handle($request);
    }
}
""",
            encoding="utf-8",
            newline="\n",
        )

        text = config.read_text(encoding="utf-8")
        if self.middleware_class not in text:
            text, count = re.subn(
                r"(['\"]http['\"]\s*=>\s*\[)",
                lambda match: match.group(1) + "\n        " + self.middleware_class + ",",
                text,
                count=1,
            )
            if count != 1:
                raise ValueError("Unable to register Hyperf HTTP middleware safely")
            config.write_text(text, encoding="utf-8", newline="\n")
        return [middleware, config]
