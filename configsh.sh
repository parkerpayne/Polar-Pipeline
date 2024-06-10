RSRC_DIR="$PWD/services/web/polarpipeline/resources"
if [ ! -f "$RSRC_DIR/config.ini" ]; then
    if [ -f "$RSRC_DIR/config.ini.example" ]; then
        cp "$RSRC_DIR/config.ini.example" "$RSRC_DIR/config.ini"
        echo "Copied config.ini.example to config.ini"
    else
        echo "Error: config.ini does not exist and config.ini.example is missing."
        exit 1
    fi
fi
