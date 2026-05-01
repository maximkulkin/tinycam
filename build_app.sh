#!/bin/bash
set -e

cd "$(dirname "$0")"
mkdir -p build

# Build ICNS icon from source PNG
echo "Building app icon..."
rm -rf build/TinyCAM.iconset
mkdir build/TinyCAM.iconset
sips -z 16   16   tinycam_icon.png --out build/TinyCAM.iconset/icon_16x16.png
sips -z 32   32   tinycam_icon.png --out build/TinyCAM.iconset/icon_16x16@2x.png
sips -z 32   32   tinycam_icon.png --out build/TinyCAM.iconset/icon_32x32.png
sips -z 64   64   tinycam_icon.png --out build/TinyCAM.iconset/icon_32x32@2x.png
sips -z 128  128  tinycam_icon.png --out build/TinyCAM.iconset/icon_128x128.png
sips -z 256  256  tinycam_icon.png --out build/TinyCAM.iconset/icon_128x128@2x.png
sips -z 256  256  tinycam_icon.png --out build/TinyCAM.iconset/icon_256x256.png
sips -z 512  512  tinycam_icon.png --out build/TinyCAM.iconset/icon_256x256@2x.png
sips -z 512  512  tinycam_icon.png --out build/TinyCAM.iconset/icon_512x512.png
sips -z 1024 1024 tinycam_icon.png --out build/TinyCAM.iconset/icon_512x512@2x.png
iconutil -c icns build/TinyCAM.iconset -o build/TinyCAM.icns
rm -rf build/TinyCAM.iconset

# Build Cython extension if source is newer than compiled output
if [ ! -f tinycam/ui/view_items/core/_line2d_cy*.so ] || \
   [ tinycam/ui/view_items/core/_line2d_cy.pyx -nt tinycam/ui/view_items/core/_line2d_cy*.so ]; then
    echo "Building Cython extension..."
    python setup.py build_ext --inplace --build-lib build/cython
fi

echo "Running PyInstaller..."
pyinstaller TinyCAM.spec --noconfirm --workpath build/pyinstaller --distpath build

echo ""
echo "Done. App bundle: build/TinyCAM.app"
