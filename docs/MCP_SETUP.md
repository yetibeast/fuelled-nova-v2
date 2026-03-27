# Nova MCP Server Setup

## Claude Desktop
Add to claude_desktop_config.json:
```json
{
  "mcpServers": {
    "fuelled-nova": {
      "url": "http://localhost:8150/mcp"
    }
  }
}
```

## Claude Code
The MCP server is available at http://localhost:8150/mcp when running locally.

## Running the server
```bash
cd backend
pip install fastmcp
python mcp_server.py
```

## What it provides
6 tools for equipment valuation:
- **search_comparables**: Search 36K+ listings by keywords, category, and price range
- **get_category_stats**: Category pricing statistics (count, avg, min, max)
- **lookup_rcn**: Replacement cost lookup from gold reference tables
- **calculate_fmv**: Deterministic FMV calculation with depreciation factors
- **check_equipment_risks**: Risk factor assessment (idle, PLC, cross-border, etc.)
- **fetch_listing**: Read equipment listing URLs and extract specs
