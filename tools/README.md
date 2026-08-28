# Verification tools

The LUKS unlock screen cannot be previewed from a running session — it only
renders before the encrypted root is mounted, and **starting `plymouthd` from
inside a desktop session takes over the console and leaves the machine with no
working keyboard**. Do not try it. These tools exist so the theme can be
checked without rebooting blind.

## plyparse — does it parse?

`script.so` exports the real parser, so this is not a lookalike:

```bash
gcc -o /tmp/plyparse plyparse.c -ldl
/tmp/plyparse ../theme/omarchy.script      # => PARSE OK
```

## plyrun — does it actually run?

Registers only the math and string libs, so the script under test supplies its
own stubs for `Image`, `Sprite`, `Window` and `Plymouth` (`prelude.script`),
then reads named globals back out.

```bash
gcc -o /tmp/plyrun plyrun.c -ldl
sed 's/@MODE@/boot/' prelude.script > /tmp/pre.script
cat /tmp/pre.script ../theme/omarchy.script verify.script > /tmp/t.script
/tmp/plyrun /tmp/t.script amb_alive seg_bone_alive shard_alive ui_final
```

`verify-keepout.script` asserts the ambient field never overlaps the login
block: it walks `amb.x/y/box` and counts glyphs inside the keep-out rectangle,
which must be zero at every density and every `KEEPOUT`. Placement happens at
load, so no frames need to run.

`verify.script` covers the rejected-key visuals; `verify-clock.script` covers
the paused-progress detection that decides when a key was accepted;
`verify-shutdown.script` asserts what the farewell screen must NOT build, which
is the whole boot composition — the prelude counts `Image()` calls, so a
regression there shows up as a number rather than as a slower shutdown nobody
notices.
`@MODE@` is substituted with `boot`, `shutdown` or `reboot` to exercise
`Plymouth.GetMode()`.

Two traps, both learned the hard way:

- **Check the script unpacked from the built boot image, not the copy in
  `/usr/share`.** This system boots a UKI, so:
  `objcopy -O binary --only-section=.initrd /boot/EFI/Linux/omarchy_linux.efi
  initrd.img && lsinitcpio -x initrd.img`
- **Harness loop counters must not collide with names the theme assigns inside
  a function.** In this language a bare assignment inside a function writes
  through to an existing global of the same name, so a test loop using `i` or
  `b` gets clobbered mid-iteration by `refresh_callback`. Use `qq`/`zz`/`qi`.

## The Limine menu — this one you can actually see

Limine is an ordinary EFI binary, so unlike Plymouth it boots in a VM and you
can screenshot it before committing anything to `/boot`.

```bash
sudo pacman -S --needed qemu-system-x86 edk2-ovmf

mkdir -p esp/EFI/BOOT esp/omarchy-nier
cp /usr/share/limine/BOOTX64.EFI esp/EFI/BOOT/BOOTX64.EFI
cp /usr/share/omarchy-plymouth-nier/limine/bg.png esp/omarchy-nier/bg.png
cp /boot/limine.conf esp/limine.conf     # the live one works as-is
sed -i 's/^timeout: .*/timeout: 60/' esp/limine.conf
cp /usr/share/edk2/x64/OVMF_VARS.4m.fd vars.fd

{ sleep 25; echo "screendump out.ppm"; sleep 5; echo quit; } | \
qemu-system-x86_64 -machine q35 -m 512 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd \
  -drive if=pflash,format=raw,file=vars.fd \
  -drive file=fat:rw:esp,format=raw \
  -vga none -device VGA,xres=1920,yres=1080,vgamem_mb=64 \
  -display none -monitor stdio > qemu.log 2>&1
magick out.ppm out.png
```

No `mtools` needed: `fat:rw:` exposes a directory as a FAT volume. `-vga none`
must come before `-device VGA` or you get two adapters, and `vgamem_mb` has to
be raised for large modes — 2880x1800x4 is 20.7 MB and the 16 MB default
silently refuses the mode.

**It verifies composition, not resolution.** The screen mode is handed to QEMU
on the command line, so any conclusion that depends on it is circular. That
already cost a round: a `term_font_scale` derived from the panel size looked
right in a screenshot here and was far too large on real firmware, because
Limine picks its own GOP mode. Use this for palette, transparency, brackets,
the entry tree and whether the config parses.

Reading the source was not enough either. Only booting it revealed a second
help row (`S Firmware Setup   B Blank Entry`) and that an entry's `comment:`
is drawn at the foot of the screen rather than beside the entry.

## Previews

`preview-arranque.html` and `preview-apagado.html` are canvas simulations of
the boot and shutdown screens, used to agree on the design before baking it
into the boot image. They carry the same `SCALE` constant as `build-theme.py`.
`preview-bootloader.html` does the same for the Limine menu, on a real 8x16
character grid quantised to 1 bit; its resolution selector models the
*wallpaper*, which is per-resolution, not the mode the menu will run at.
