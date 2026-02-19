import importlib.util
import os

spec = importlib.util.spec_from_file_location('main', os.path.join(os.path.dirname(__file__), '..', 'main.py'))
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

events = main.parse_midi('sample/sample.mid')
main.export_mcr('sample/generated_by_app.mcr', events)
print('Wrote sample/generated_by_app.mcr with', len(events), 'events')
