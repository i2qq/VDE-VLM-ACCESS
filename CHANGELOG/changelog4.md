# Changelog 4 - MCP Server Configuration & Global VDE Testing Rule

### Summary
Plugged in the `vde-vlm` Model Context Protocol (MCP) server into Antigravity's global configuration and registered an `always_on` rule so Gemini keeps active context on how to observe, control, and test Victorious Desktop Environment across sessions.

### Highlights & Modifications
1. **MCP Server Integration (`C:\Users\Victor\.gemini\config\mcp_config.json`)**:
   - Plugged in `vde-vlm` MCP server over stdio running `python -m vde_vlm.server`.
   - Exposes tools: `vm_list`, `vm_start`, `vm_stop`, `vm_observe`, `vm_click`, `vm_type`, `vm_key`, `vm_batch`, `vm_exec`, `vm_snapshot`, `vm_restore`, `vm_clean`.
2. **Persistent Rule (`C:\Users\Victor\.gemini\config\rules\vde-vlm-virtualbox-access.md`)**:
   - Added rule with `trigger: always_on` to ensure full context retention for VM testing, collaborative live studio on port 7891, safety snapshots, compound batch macro execution, and storage hygiene.
   - Versioned inside repository under `rules/vde-vlm-virtualbox-access.md`.
