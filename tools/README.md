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

`verify.script` covers the rejected-key visuals; `verify-clock.script` covers
the paused-progress detection that decides when a key was accepted.
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

## Previews

`preview-arranque.html` and `preview-apagado.html` are canvas simulations of
the boot and shutdown screens, used to agree on the design before baking it
into the boot image. They carry the same `SCALE` constant as `build-theme.py`.
