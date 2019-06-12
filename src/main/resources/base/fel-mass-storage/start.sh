#!/bin/bash

cd "$FEL_DIR"

BOARD=h3

OSNAME="$(uname -s)"
if [[ "$OSNAME" == "Darwin"* ]]; then
	export DYLD_LIBRARY_PATH="$LIB_PATH":$DYLD_LIBRARY_PATH
fi

"$SUNXI_FEL" -p uboot $BOARD/u-boot-sunxi-with-spl.bin write 0x42000000 $BOARD/zImage write 0x43000000 $BOARD/script.bin write 0x43300000 $BOARD/uInitrd write 0x43100000 $BOARD/boot.scr
