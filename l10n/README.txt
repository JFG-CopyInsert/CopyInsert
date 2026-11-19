Translating CopyInsert
======================

Three files per language ("xx" is the two-letter language code, for example "de"):

  1. l10n/CopyInsert_xx.properties     the texts of the macros: menus, messages, Undo titles
  2. registry/Addons_xx.xcu            the four titles of the entries in the Edit menu
  3. description/description_xx.txt    the text shown in Tools > Extension Manager

English is the default: l10n/CopyInsert_en_US.properties, the English titles in
registry/Addons.xcu and description/description_en.txt. French is the example of a
finished translation (CopyInsert_fr.properties, Addons_fr.xcu, description_fr.txt).

Anything missing from a language is shown in English, so a partial translation works.
A language without any file is shown in English.

Also list the new files in two index files (one line each, copy the French lines):

  META-INF/manifest.xml   Addons_xx.xcu and description_xx.txt
  description.xml         <name lang="xx"> (display name) and <src lang="xx" .../>

A fourth file is optional: license/license_xx.txt, a translation of the license, with one
more <license-text ... lang="xx" license-id="xx"/> line in description.xml (copy the French
line). If the user interface language has no license text, the English one is shown
(default-license-id="en"; every <license-text> must carry its license-id).

Nothing else changes; the Basic module and the Python files are not touched.


1. CopyInsert_xx.properties
---------------------------
  - Copy CopyInsert_en_US.properties and translate what follows each "=".
  - Do not change the keys (the part before the "=").
  - Keep the "~". The letter after it is the keyboard letter of the entry. Inside one
    submenu the letters must be different (dir.above, dir.below, dir.left, dir.right).
  - The files are read as ASCII. Write every accented or special character as \uXXXX,
    for example e-acute = \u00e9, a-grave = \u00e0, c-cedilla = \u00e7, o-e ligature = \u0153,
    sharp s = \u00df, a-umlaut = \u00e4, o-umlaut = \u00f6, u-umlaut = \u00fc.
    To convert a UTF-8 text with Python:
      python3 -c "import sys; print(''.join(c if ord(c)<128 else '\\u%04x'%ord(c) for c in sys.stdin.read()),end='')" < in.txt > out.txt
  - A space at the end of a value is written \u0020 (see undo.prefix).
  - A country version is used before the language file: CopyInsert_fr_CA.properties
    for French (Canada), CopyInsert_fr.properties for every other French.

2. Addons_xx.xcu
----------------
  Copy Addons_fr.xcu, change xml:lang="fr" to your code and translate the four titles.
  LibreOffice shows the title that matches the user interface language. Keep
  oor:op="fuse" everywhere (in Addons.xcu too): it is what merges your titles into the
  menu entries defined in Addons.xcu.

3. description_xx.txt
---------------------
  Plain text, UTF-8. Copy description_en.txt and translate it.

Testing
-------
  Install the extension (Tools > Extension Manager > Add), set the user interface
  language (Tools > Options > Language Settings > Languages), restart LibreOffice and
  open a spreadsheet. Check the right-click menu and the Edit menu. The macro
  ShowLanguage (Application Macros > My Macros > CopyInsertLib > CopyInsert) shows which
  file is used.
