#!/usr/bin/env sh
#
# install-path.sh
# Installs vde-vlm launcher into ~/.local/bin and verifies PATH for sh/bash.
#

set -e

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

PYTHON_BIN="$(which python3 || which python || echo "python")"

cat <<EOF > "$BIN_DIR/vde-vlm"
#!/usr/bin/env sh
exec "$PYTHON_BIN" -m vde_vlm "\$@"
EOF

chmod +x "$BIN_DIR/vde-vlm"

echo "[OK] Installed $BIN_DIR/vde-vlm"
echo "Ensure $BIN_DIR is in your PATH in ~/.bashrc or ~/.zshrc:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
