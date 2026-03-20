#!/bin/bash
# =============================================================================
# Security Scan Suite for Impuestify
# Runs OWASP ZAP (DAST) + Nuclei (template scanner) against target URL
#
# Usage:
#   ./scripts/security-scan.sh                    # scan localhost:8000
#   ./scripts/security-scan.sh https://staging.impuestify.com  # scan staging
#   ./scripts/security-scan.sh --zap-only         # only OWASP ZAP
#   ./scripts/security-scan.sh --nuclei-only      # only Nuclei
# =============================================================================

set -e

TARGET="${1:-http://host.docker.internal:8000}"
REPORT_DIR="plans/security-reports"
DATE=$(date +%Y-%m-%d)
ZAP_ONLY=false
NUCLEI_ONLY=false

# Parse flags
for arg in "$@"; do
    case $arg in
        --zap-only) ZAP_ONLY=true; TARGET="${2:-http://host.docker.internal:8000}" ;;
        --nuclei-only) NUCLEI_ONLY=true; TARGET="${2:-http://host.docker.internal:8000}" ;;
        http*) TARGET="$arg" ;;
    esac
done

mkdir -p "$REPORT_DIR"

echo "======================================"
echo "  Impuestify Security Scan"
echo "  Target: $TARGET"
echo "  Date: $DATE"
echo "======================================"

# --- OWASP ZAP (API Scanner) ---
if [ "$NUCLEI_ONLY" = false ]; then
    echo ""
    echo "[1/2] OWASP ZAP — API Security Scan"
    echo "  Scanning OpenAPI endpoints..."

    docker run --rm \
        --add-host=host.docker.internal:host-gateway \
        -v "$(pwd)/$REPORT_DIR:/zap/wrk:rw" \
        ghcr.io/zaproxy/zaproxy:stable \
        zap-api-scan.py \
        -t "$TARGET/openapi.json" \
        -f openapi \
        -r "zap-report-${DATE}.html" \
        -J "zap-report-${DATE}.json" \
        -l WARN \
        -z "-config api.disablekey=true" \
        2>&1 | tail -20

    echo "  ZAP report: $REPORT_DIR/zap-report-${DATE}.html"
fi

# --- Nuclei (Template Scanner) ---
if [ "$ZAP_ONLY" = false ]; then
    echo ""
    echo "[2/2] Nuclei — Template-based Vulnerability Scan"
    echo "  Running 11,000+ templates..."

    docker run --rm \
        --add-host=host.docker.internal:host-gateway \
        -v "$(pwd)/$REPORT_DIR:/output:rw" \
        projectdiscovery/nuclei:latest \
        -u "$TARGET" \
        -severity medium,high,critical \
        -tags cve,misconfig,exposure,token \
        -exclude-tags dos \
        -j -o "/output/nuclei-report-${DATE}.json" \
        2>&1 | tail -20

    echo "  Nuclei report: $REPORT_DIR/nuclei-report-${DATE}.json"
fi

echo ""
echo "======================================"
echo "  Scan complete. Reports in: $REPORT_DIR/"
echo "======================================"
