source ~/src/badge-2024-software/venv/bin/activate

mpremote fs mkdir apps/scripter

for a in "" steps/ pickers/; do
  mpremote fs mkdir apps/scripter/${a}
  mpremote fs cp --verbose ~/src/tildagon-sequencer/${a}*.py :apps/scripter/${a}
done

for a in metadata.json tildagon.toml; do
  mpremote fs cp --verbose ~/src/tildagon-sequencer/${a} :apps/scripter/
done
