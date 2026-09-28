; toy.asm - a minimal joypad-controlled square, built for end-to-end tests.
;
; No copyrighted material: this is original test homebrew, built with RGBDS.
;
;   d-pad  moves the square one pixel per frame
;   A      inverts the palette (whole-screen flash)
;   B      restores the palette
;   Start  resets the square to the center

SECTION "Entry", ROM0[$100]
    nop
    jp Start
    ds $150 - @, 0        ; header space, filled by rgbfix

SECTION "Main", ROM0[$150]
Start:
    di
.waitOff:                 ; wait for vblank, then turn the LCD off
    ldh a, [$FF44]          ; LY
    cp 144
    jr c, .waitOff
    xor a
    ldh [$FF40], a          ; LCDC = off

    ; tile 1 = solid block (tile 0 stays blank)
    ld hl, $8010
    ld b, 16
.tileLoop:
    ld a, $FF
    ld [hl+], a
    dec b
    jr nz, .tileLoop

    ld a, $E4             ; normal 4-shade palette
    ldh [$FF47], a          ; BGP
    ldh [$FF48], a          ; OBP0

    ; clear the BG map (the boot ROM leaves its logo behind)
    ld hl, $9800
    ld bc, $0400
.clearMap:
    xor a
    ld [hl+], a
    dec bc
    ld a, b
    or c
    jr nz, .clearMap

    call ResetSprite

    ld a, $93             ; LCD on, BG on, sprites on, tiles at $8000
    ldh [$FF40], a

MainLoop:
    call WaitVBlank

    ; --- d-pad: move the square ---
    ld a, $20
    ldh [$FF00], a          ; select d-pad
    ldh a, [$FF00]
    ldh a, [$FF00]          ; read twice to settle
    cpl                   ; buttons are active-low
    and $0F
    ld b, a

    bit 0, b              ; right
    jr z, .notRight
    ld a, [$FE01]
    inc a
    ld [$FE01], a
.notRight:
    bit 1, b              ; left
    jr z, .notLeft
    ld a, [$FE01]
    dec a
    ld [$FE01], a
.notLeft:
    bit 2, b              ; up
    jr z, .notUp
    ld a, [$FE00]
    dec a
    ld [$FE00], a
.notUp:
    bit 3, b              ; down
    jr z, .notDown
    ld a, [$FE00]
    inc a
    ld [$FE00], a
.notDown:

    ; --- buttons ---
    ld a, $10
    ldh [$FF00], a          ; select buttons
    ldh a, [$FF00]
    ldh a, [$FF00]
    cpl
    and $0F
    ld b, a               ; current buttons
    ld a, [$C000]         ; previous buttons
    ld c, a
    ld a, b
    ld [$C000], a
    ld a, c
    cpl
    and b                 ; newly pressed = current & ~previous
    ld b, a

    bit 0, b              ; A: invert the palette
    jr z, .notA
    ldh a, [$FF47]
    cpl
    ldh [$FF47], a
    ldh [$FF48], a
.notA:
    bit 1, b              ; B: restore the palette
    jr z, .notB
    ld a, $E4
    ldh [$FF47], a
    ldh [$FF48], a
.notB:
    bit 3, b              ; Start: back to center
    jr z, .notStart
    call ResetSprite
.notStart:
    jr MainLoop

WaitVBlank:               ; one call = one frame
.waitOut:                 ; leave the current vblank first
    ldh a, [$FF44]
    cp 144
    jr nc, .waitOut
.waitIn:
    ldh a, [$FF44]
    cp 144
    jr c, .waitIn
    ret

ResetSprite:              ; OAM sprite 0 at screen center
    ld a, 72 + 16
    ld [$FE00], a         ; y (OAM y is screen y + 16)
    ld a, 80 + 8
    ld [$FE01], a         ; x (OAM x is screen x + 8)
    ld a, 1
    ld [$FE02], a         ; tile 1
    xor a
    ld [$FE03], a         ; flags
    ret
