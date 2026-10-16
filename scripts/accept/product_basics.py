#!/usr/bin/env python3
"""Installed MacKit basics; existing offscreen/CLI paths with private home, domain and cloud."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
APP = Path('/Applications/MacKit.app')
PRODUCT = 'cyou.tianli.mackit'
FEATURES = ('settings', 'shortcuts', 'icloud', 'updates')
RECEIPT = ROOT / 'perf/build-receipt.json'
# Policy scenario names are summaries of actual assertions below; never independent constants claiming success.
SCENARIOS = {
    'settings': {
        'interaction': ['profile_selection', 'valid_import', 'config-light.upgrade_native_titlebar'],
        'persisted_readback': ['export_contains_saved_selection', 'import_readback_in_app_adapter', 'real_running_window_follows_cli'],
        'error_preserves_data': ['invalid_import_rejected', 'invalid_import_preserves_original'],
    },
    'shortcuts': {
        'action_path': ['fresh_action_readback', 'real_action_command_rendered', 'component_filter'],
        'disable_restore': ['disable', 'disabled_readback', 'restore', 'restored_readback'],
        'conflict_or_reserved_keys': ['duplicate_refused', 'window_conflict_hint', 'recorder_focus_cleanup'],
    },
    'icloud': {
        'push_pull': ['enable_and_push', 'local_configuration_reached_fixture', 'receive_remote_change', 'remote_value_applied'],
        'unavailable_local_fallback': ['unavailable_reports_error', 'unavailable_preserves_local', 'disabled_local_readback'],
        'conflict_or_corrupt_recovery': ['local_conflict_wins_remote_independent_field_merges', 'bad_remote_reports_error', 'bad_remote_preserves_local', 'recover_after_bad_remote'],
        'disable_preserves_data': ['disable', 'disable_preserves_both_copies'],
    },
    'updates': {
        'check_result': ['test_feed_update_and_get_entry', 'updates-light.actual_check_button'],
        'failure_recovery': ['missing_feed_error', 'corrupt_feed_error', 'test_feed_update_and_get_entry'],
        'options_or_store_entry': ['options_default_off', 'save_options', 'fresh_options_readback', 'invalid_interval_refused'],
        'data_preservation': ['failed_checks_and_preview_preserve_data', 'production_configuration_and_installed_bytes_unchanged'],
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def owner_snapshot():
    """Hashes only: production configuration/keys, defaults and installed bytes are never written."""
    paths = [Path.home() / '.config/mackit', ROOT / 'components']
    result = {}
    for root in paths:
        for path in root.rglob('*'):
            if path.is_symlink():
                result[str(path)] = 'link:' + os.readlink(path)
            elif path.is_file():
                result[str(path)] = sha(path)
    for name in ('karabiner/karabiner.json', 'skhd/skhdrc', 'yabai/yabairc'):
        path = Path.home() / '.config' / name
        result[str(path)] = sha(path) if path.is_file() else None
    result['installed-main'] = sha(APP / 'Contents/MacOS/MacKit')
    prefs = subprocess.run(['/usr/bin/defaults', 'export', PRODUCT, '-'], capture_output=True)
    result['production-defaults'] = (hashlib.sha256(plistlib.dumps(plistlib.loads(prefs.stdout), sort_keys=True)).hexdigest()
                                     if prefs.returncode == 0 else None)
    return result


def main():
    spec = json.loads(os.environ['SOP_PRODUCT_BASICS_SPEC'])
    assert os.environ['SOP_APP_ID'] == 'mackit' and spec['app_id'] == 'mackit'
    out = Path(os.environ['SOP_OUT_DIR']).resolve()
    assert out.is_relative_to(ROOT / 'perf/acceptance'), 'Evidence must stay in product acceptance directory'
    run = out / ('product-basics-' + uuid.uuid4().hex)
    run.mkdir(parents=True)
    checks = {key: {} for key in FEATURES}
    cases = {key: [] for key in FEATURES}
    error = None
    installed = {}
    before = owner_snapshot()
    write(run / 'owner-before.json', before)
    suite = 'test.tianli.mackit.basics.' + uuid.uuid4().hex
    binding = {}

    def check(feature, name, condition):
        checks[feature][feature + '.' + name] = bool(condition)

    try:
        receipt = json.loads(RECEIPT.read_text())
        artifact = receipt['artifact']
        info = plistlib.loads((APP / 'Contents/Info.plist').read_bytes())
        installed = {'version': info['CFBundleShortVersionString'], 'build': info['CFBundleVersion'],
                     'bundle_id': info['CFBundleIdentifier'], 'sha256': sha(APP / artifact['executable'])}
        matched = (installed['bundle_id'] == artifact['bundle_id'] == PRODUCT
                   and installed['version'] == artifact['version'] == (ROOT / 'VERSION').read_text().strip()
                   and installed['build'] == artifact['build'] and installed['sha256'] == artifact['sha256'])
        source_matches = all((ROOT / path).is_file() and sha(ROOT / path) == digest
                             for path, digest in receipt['source']['files'].items())
        signature = subprocess.run(['codesign', '--verify', '--deep', '--strict', str(APP)], capture_output=True, text=True)
        (run / 'installed-signature.log').write_text(signature.stdout + signature.stderr)
        binding = {'receipt': str(RECEIPT.relative_to(ROOT)), 'receipt_sha256': sha(RECEIPT),
                   'source_sha256': receipt['source']['sha256'], 'source_commit': receipt['source']['commit'],
                   'acceptor_sha256': sha(Path(__file__)), 'lifecycle_tests_sha256': sha(ROOT / 'tests/test_lifecycle_cli.py')}
        for feature in FEATURES:
            check(feature, 'installed_matches_receipt', matched)
            check(feature, 'source_matches_installed_receipt', source_matches)
            check(feature, 'installed_signature_valid', signature.returncode == 0)
        assert matched and source_matches and signature.returncode == 0, 'Installed/source/receipt/signature mismatch; no fixture execution'

        clone = run / 'fixture/MacKit.app'
        clone.parent.mkdir()
        shutil.copytree(APP, clone, symlinks=True)
        check('settings', 'fixture_copied_installed_bytes', sha(clone / artifact['executable']) == installed['sha256'])
        info.update(CFBundleIdentifier=suite, LSUIElement=True)
        (clone / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
        subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(clone)], capture_output=True, check=True, timeout=60)
        env = {k: v for k, v in os.environ.items() if not k.startswith(('APP_LIFECYCLE_', 'MACKIT_LIFECYCLE_', 'MACKIT_NATIVE'))}
        env.update(APP_LIFECYCLE_SUPPORT_DIR=str(run / 'support'), APP_LIFECYCLE_CLOUD_DIR=str(run / 'cloud'),
                   MACKIT_LIFECYCLE_SUITE=suite, PYTHONDONTWRITEBYTECODE='1', APP_LIFECYCLE_NO_RELAUNCH='1')
        home = run / ('mackit-accept-' + uuid.uuid4().hex)
        home.mkdir()
        cli = clone / 'Contents/Resources/core/bin/mackit'
        ui_env = dict(env, SOP_OUT_DIR=str(run / 'ui'))
        ui_done = subprocess.run([str(clone / 'Contents/MacOS/MacKit'), '--ui-self-test', '--demo-home', str(home)],
                                 env=ui_env, cwd=ROOT, capture_output=True, text=True, timeout=90)
        (run / 'ui.log').write_text(ui_done.stdout + ui_done.stderr)
        ui = json.loads(ui_done.stdout)
        write(run / 'ui.json', ui)
        check('settings', 'real_offscreen_suite', ui_done.returncode == 0 and ui.get('ok') is True)
        for name in ('refresh_real_engine', 'profile_selection', 'discard_draft', 'never_visible_or_key', 'close_action'):
            check('settings', name, ui.get('checks', {}).get(name) is True)
        for name in ('component_filter', 'empty_search', 'window_conflict_hint', 'recorder_focus_cleanup'):
            check('shortcuts', name, ui.get('checks', {}).get(name) is True)
        for appearance in ('config-light', 'config-dark'):
            for name in ('upgrade_native_titlebar', 'upgrade_window_offscreen', 'upgrade_image_rendered'):
                check('settings', appearance + '.' + name, ui['checks'].get(appearance + '.' + name) is True)
        for appearance in ('updates-light', 'updates-dark'):
            check('updates', appearance + '.actual_check_button', ui['checks'].get(appearance + '.upgrade_actual_button_target') is True)
        check('updates', 'busy_and_unsaved_protection', all(ui['checks'].get(k) is True for k in
                                                         ('update_busy_gate', 'update_cli_busy_gate', 'update_unsaved_gate', 'update_clean_gate')))

        def call(feature, label, words, predicate, code=0, override=None):
            done = subprocess.run([str(cli), '--home', str(home), *words, '--json'], env=override or env,
                                  cwd=ROOT, capture_output=True, text=True, timeout=30)
            body = json.loads(done.stdout)
            passed = done.returncode == code and bool(predicate(body))
            check(feature, label, passed)
            cases[feature].append({'case': feature + '.' + label, 'argv': words, 'exit': done.returncode,
                                   'passed': passed, 'response': body, 'stderr': done.stderr})
            return body

        # The CLI writes the very adapter used by the real settings window; every read is a new process.
        call('settings', 'save_selection', ['select', '--profile', 'tianli', '--components', 'nvim,zsh'],
             lambda b: b.get('components') == ['nvim', 'zsh'])
        selected = home / '.config/mackit/portable-preferences.json'
        exported = run / 'export.json'
        call('settings', 'export', ['config', 'export', '-o', str(exported)], lambda b: b.get('ok') is True)
        envelope = json.loads(exported.read_text())
        check('settings', 'export_contains_saved_selection', envelope['values'] == {'file.0.profile': 'tianli', 'file.0.components': ['nvim', 'zsh']})
        call('settings', 'fresh_process_readback', ['config', 'status'], lambda b: b.get('has_settings') is True and not b['sync_enabled'])
        baseline = selected.read_bytes()
        incoming = run / 'incoming.json'
        write(incoming, {'version': 1, 'product': PRODUCT, 'values': {'file.0.profile': 'bogus'}})
        call('settings', 'invalid_import_rejected', ['config', 'import', str(incoming), '--yes'],
             lambda b: b.get('error', {}).get('code') == 'import_rejected', code=1)
        check('settings', 'invalid_import_preserves_original', selected.read_bytes() == baseline)
        write(incoming, {'version': 1, 'product': PRODUCT, 'values': {'file.0.profile': 'developer', 'file.0.components': ['tmux']}})
        call('settings', 'valid_import', ['config', 'import', str(incoming), '--yes'], lambda b: b.get('imported') is True)
        call('settings', 'import_readback_in_app_adapter', ['status'],
             lambda b: b['app']['profile'] == 'developer' and b['app']['selected'] == ['tmux'])

        call('shortcuts', 'prepare_isolated_source', ['prepare'], lambda b: b.get('ok') is True)
        key = 'ctrl+alt+shift+f9'
        call('shortcuts', 'persist_action', ['window', 'hotkey', 'add', '--key', key, '--action', 'full'],
             lambda b: isinstance(b.get('conflicts'), list))
        def has_key(b):
            return any(k.get('key') == key and k.get('action') == 'full' for k in b['window']['hotkeys'])
        call('shortcuts', 'fresh_action_readback', ['window', 'status'], has_key)
        call('shortcuts', 'duplicate_refused', ['window', 'hotkey', 'add', '--key', key, '--action', 'left'], lambda b: 'error' in b, code=1)
        call('shortcuts', 'disable', ['window', 'hotkey', 'remove', '--key', key], lambda b: b.get('ok') is True)
        call('shortcuts', 'disabled_readback', ['window', 'status'], lambda b: not any(k.get('key') == key for k in b['window']['hotkeys']))
        call('shortcuts', 'restore', ['window', 'hotkey', 'add', '--key', key, '--action', 'full'], lambda b: b.get('ok') is True)
        call('shortcuts', 'restored_readback', ['window', 'status'], has_key)
        skhd = home / '.local/share/mackit/components/yabai/config/skhd/skhdrc'
        check('shortcuts', 'real_action_command_rendered', 'ctrl + alt + shift - f9 : $HOME/.config/yabai/scripts/window/position.sh full' in skhd.read_text())

        # iCloud Drive transport is injected as a private directory. No Apple account or production cloud is opened.
        def reconcile(label, code=0, override=None):
            # MacKit deliberately exposes on/off, not a `sync now` command; the real switch starts reconciliation.
            call('icloud', label + '.off', ['config', 'sync', 'off', '--yes'], lambda b: b.get('sync_enabled') is False)
            return call('icloud', label, ['config', 'sync', 'on', '--yes'], lambda b: b.get('ok') is (code == 0),
                        code=code, override=override)

        call('icloud', 'enable_and_push', ['config', 'sync', 'on', '--yes'], lambda b: b.get('sync_enabled') is True)
        cloud = run / 'cloud' / (PRODUCT + '.json')
        check('icloud', 'local_configuration_reached_fixture', json.loads(cloud.read_text())['values']['file.0.components'] == ['tmux'])
        remote = json.loads(cloud.read_text())
        remote['values']['file.0.components'] = ['ghostty']
        write(cloud, remote)
        reconcile('receive_remote_change')
        check('icloud', 'remote_value_applied', json.loads(selected.read_text())['components'] == ['ghostty'])
        call('icloud', 'concurrent_local_edit', ['select', '--profile', 'developer', '--components', 'zsh'], lambda b: b.get('ok') is True)
        remote['values']['file.0.components'] = ['nvim']
        remote['values']['file.0.profile'] = 'tianli'
        write(cloud, remote)
        reconcile('reconcile_conflict')
        value = json.loads(selected.read_text())
        check('icloud', 'local_conflict_wins_remote_independent_field_merges', value == {'profile': 'tianli', 'components': ['zsh']})
        before_bad = selected.read_bytes()
        good_cloud = cloud.read_bytes()
        cloud.write_text('{broken')
        reconcile('bad_remote_reports_error', code=1)
        check('icloud', 'bad_remote_preserves_local', selected.read_bytes() == before_bad)
        cloud.write_bytes(good_cloud)
        reconcile('recover_after_bad_remote')
        unavailable = dict(env, APP_LIFECYCLE_CLOUD_DIR=str(run / 'unavailable-cloud'))
        (run / 'unavailable-cloud').write_text('not a directory')
        reconcile('unavailable_reports_error', code=1, override=unavailable)
        check('icloud', 'unavailable_preserves_local', selected.read_bytes() == before_bad)
        call('icloud', 'disable', ['config', 'sync', 'off', '--yes'], lambda b: b.get('sync_enabled') is False)
        check('icloud', 'disable_preserves_both_copies', selected.read_bytes() == before_bad and cloud.read_bytes() == good_cloud)
        call('icloud', 'disabled_local_readback', ['status'], lambda b: b['app']['profile'] == 'tianli' and b['app']['selected'] == ['zsh'])

        call('updates', 'options_default_off', ['update', 'options'], lambda b: not any(b['options'][k] for k in ('automaticCheck', 'automaticDownload', 'automaticInstall')))
        call('updates', 'save_options', ['update', 'options', '--interval', '6', '--auto-download', 'on', '--yes'], lambda b: b.get('ok') is True)
        call('updates', 'fresh_options_readback', ['update', 'options'], lambda b: b['options']['intervalHours'] == 6 and b['options']['automaticDownload'] is True)
        call('updates', 'invalid_interval_refused', ['update', 'options', '--interval', '0', '--yes'], lambda b: b.get('ok') is False, code=2)
        feed = run / 'cloud/TianliApps/Updates' / suite / 'isolated/release.json'
        feed.parent.mkdir(parents=True, exist_ok=True)
        call('updates', 'missing_feed_error', ['update', 'check'], lambda b: b.get('error', {}).get('code') == 'check_incomplete', code=1)
        feed.write_text('{broken')
        call('updates', 'corrupt_feed_error', ['update', 'check'], lambda b: b.get('ok') is False, code=1)
        # A genuine local asset/digest, for check and dry-run only; it is never downloaded or installed.
        asset = feed.parent / 'fixture.txt'
        asset.write_text('Product basics check-only release fixture\n')
        fixture_release = {'version': installed['version'], 'build': str(int(installed['build']) + 1), 'bundle_id': suite,
                           'channel': 'isolated', 'filename': asset.name, 'sha256': sha(asset), 'size_bytes': asset.stat().st_size}
        write(feed, fixture_release)
        call('updates', 'test_feed_update_and_get_entry', ['update', 'check'],
             lambda b: b['state'] == 'update_available' and b['current'] == {'version': installed['version'], 'build': installed['build']}
             and b['upgrade']['in_app'] is True and b['upgrade']['command'] == 'mackit update install --yes')
        call('updates', 'preview_only', ['update', 'install', '--dry-run'], lambda b: b.get('installed') is False and b.get('dry_run') is True)
        check('updates', 'failed_checks_and_preview_preserve_data', selected.read_bytes() == before_bad)

        # Existing assembled-bundle regression exercises the production window/CLI follow actions offscreen.
        tmp = run / 'regression-tmp'
        tmp.mkdir()
        test_env = dict(env, TMPDIR=str(tmp), MACKIT_NATIVE=str(APP / 'Contents/MacOS/MacKit'), MACKIT_APP=str(APP))
        regression = subprocess.run([sys.executable, str(ROOT / 'tests/test_lifecycle_cli.py'),
                                     'AssembledBundleTests.test_the_bundles_own_executable_follows_its_own_command', '-v'],
                                    env=test_env, cwd=ROOT, capture_output=True, text=True, timeout=150)
        (run / 'assembled-follow.log').write_text(regression.stdout + regression.stderr)
        passed = regression.returncode == 0 and 'OK' in regression.stderr and 'skipped' not in regression.stderr
        for feature in ('settings', 'icloud', 'updates'):
            check(feature, 'real_running_window_follows_cli', passed)
        binding['upstream_ui'] = {'path': str((run / 'ui.json').relative_to(ROOT)), 'sha256': sha(run / 'ui.json')}
        binding['upstream_follow_log'] = {'path': str((run / 'assembled-follow.log').relative_to(ROOT)), 'sha256': sha(run / 'assembled-follow.log')}
    except Exception as exc:
        error = str(exc)
        for feature in FEATURES:
            check(feature, 'execution_completed', False)
    finally:
        subprocess.run(['/usr/bin/defaults', 'delete', suite], capture_output=True, timeout=15)
        after = owner_snapshot()
        write(run / 'owner-after.json', after)
        for feature in FEATURES:
            check(feature, 'production_configuration_and_installed_bytes_unchanged', after == before)

    scope = ('Installed binary/engine, private re-identified copy and preference domain; real native views rendered offscreen, '
             'actual CLI/action and follow paths. Shortcut configuration/action declarations are exercised without dispatching '
             'keys to the desktop. iCloud is a local directory fixture: Apple server/cross-device delivery was not tested. '
             'Update release fixture, options and dry-run only; no build, product installation, release or network download.')
    details = {}
    for feature in FEATURES:
        for name, dependencies in SCENARIOS[feature].items():
            check(feature, name, all(checks[feature].get(feature + '.' + key) is True for key in dependencies))
        raw = {'schema_version': 1, 'app_id': 'mackit', 'spec_digest': spec['digest'], 'checks': checks[feature],
               'checked_at': time.time(), 'installed': installed, 'binding': binding, 'cases': cases[feature],
               'scope': scope, 'error': error, 'scenario_assertions': SCENARIOS[feature]}
        path = run / (feature + '.json')
        write(path, raw)
        details[feature] = {'result': 'passed' if checks[feature] and all(checks[feature].values()) else 'failed',
                            'method': 'ui_automation' if feature == 'settings' else 'real_product',
                            'evidence': str(path.relative_to(ROOT)), 'evidence_sha256': sha(path), 'checks': list(checks[feature])}
    passed = all(row['result'] == 'passed' for row in details.values())
    count = sum(len(row) for row in checks.values())
    detail = {'schema_version': 1, 'app_id': 'mackit', 'spec_digest': spec['digest'], 'features': details, 'scope': scope,
              'summary': f'MacKit 基本功能{"通过" if passed else "失败"}；{count} 项检查（含14项场景汇总）；iCloud 为隔离文件链路，未验苹果跨设备传输'}
    if error:
        detail['error'] = error
    write(out / 'product_basics.detail.json', detail)
    print(detail['summary'])
    if error:
        print(error, file=sys.stderr)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
