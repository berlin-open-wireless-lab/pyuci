from pyuci import Uci, Diff
import os.path
import unittest
import json

class TestSetup(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        path,filename = os.path.split(os.path.realpath(__file__))
        self.confstring = open(os.path.join(path,'example_config')).read()
        self.confa = Uci()
        self.confb = Uci()
        self.confa.load_tree(self.confstring)
        self.confb.load_tree(self.confstring)

    def test_sameconfig(self):
        result = self.confa.diff(self.confb)
        self.assertEqual(result['newpackages'], {})
        self.assertEqual(result['newconfigs'], {})
        self.assertEqual(result['oldpackages'], {})
        self.assertEqual(result['oldconfigs'], {})
        self.assertEqual(result['newOptions'], {})
        self.assertEqual(result['oldOptions'], {})
        self.assertEqual(result['chaOptions'], {})

        jsonExport = result.exportJson()
        self.assertEqual(json.loads(jsonExport), json.loads('{"newpackages": {}, "oldpackages": {}, "newconfigs": {}, "oldconfigs": {}, "newOptions": {}, "oldOptions": {}, "chaOptions": {}}'))
        importTest = Diff()
        importTest.importJson(jsonExport)
        self.assertEqual(importTest, result)

        result.apply(self.confa)
        self.assertEqual(self.confa, self.confb)
        result.revert(self.confa)
        self.assertEqual(self.confa.diff(self.confb), result)

    def test_missing_package_in_oldconf(self):
        removed_key = list(self.confa.packages.keys())[0]
        self.confa.packages.pop(removed_key)
        result = self.confa.diff(self.confb)
        self.assertEqual(result['newpackages'], {removed_key: self.confb.packages[removed_key]})
        self.assertEqual(result['newconfigs'], {})
        self.assertEqual(result['oldpackages'], {})
        self.assertEqual(result['oldconfigs'], {})
        self.assertEqual(result['newOptions'], {})
        self.assertEqual(result['oldOptions'], {})
        self.assertEqual(result['chaOptions'], {})

        jsonExport = result.exportJson()
        packageJsonString = json.dumps(self.confb.packages[removed_key].exportDictForJson())
        expected = '{"newpackages": '
        expected += '{"' + removed_key + '": ' + packageJsonString + '}'
        expected += ', "oldpackages": {}, "newconfigs": {}, "oldconfigs": {}, "newOptions": {}, "oldOptions": {}, "chaOptions": {}}'
        self.assertEqual(json.loads(jsonExport), json.loads(expected))
        importTest = Diff()
        importTest.importJson(jsonExport)
        self.assertEqual(importTest, result)

        result.apply(self.confa)
        self.assertEqual(self.confa, self.confb)
        result.revert(self.confa)
        self.assertEqual(self.confa.diff(self.confb), result)

    def test_missing_package_in_newconf(self):
        removed_key = list(self.confa.packages.keys())[0]
        self.confb.packages.pop(removed_key)
        result = self.confa.diff(self.confb)
        self.assertEqual(result['newpackages'], {})
        self.assertEqual(result['newconfigs'], {})
        self.assertEqual(result['oldpackages'], {removed_key: self.confa.packages[removed_key]})
        self.assertEqual(result['oldconfigs'], {})
        self.assertEqual(result['newOptions'], {})
        self.assertEqual(result['oldOptions'], {})
        self.assertEqual(result['chaOptions'], {})

        packageJsonString = json.dumps(self.confa.packages[removed_key].exportDictForJson())
        expected = '{"newpackages": {}, "oldpackages": '
        expected += '{"' + removed_key + '": ' + packageJsonString + '}'
        expected += ', "newconfigs": {}, "oldconfigs": {}, "newOptions": {}, "oldOptions": {}, "chaOptions": {}}'
        jsonExport = result.exportJson()
        self.assertEqual(json.loads(jsonExport), json.loads(expected))
        importTest = Diff()
        importTest.importJson(jsonExport)
        self.assertEqual(importTest, result)

        result.apply(self.confa)
        self.assertEqual(self.confa, self.confb)
        result.revert(self.confa)
        self.assertEqual(self.confa.diff(self.confb), result)

    def test_missing_config_in_oldconf(self):
        removed_key = list(self.confa.packages.keys())[0]
        removed_conf = list(self.confa.packages[removed_key].keys())[0]
        self.confa.packages[removed_key].pop(removed_conf)
        result = self.confa.diff(self.confb)
        self.assertEqual(result['newpackages'], {})
        self.assertEqual(result['newconfigs'], {(removed_key, removed_conf): self.confb.packages[removed_key][removed_conf]})
        self.assertEqual(result['oldpackages'], {})
        self.assertEqual(result['oldconfigs'], {})
        self.assertEqual(result['newOptions'], {})
        self.assertEqual(result['oldOptions'], {})
        self.assertEqual(result['chaOptions'], {})

        jsonExport = result.exportJson()
        configJsonString = json.dumps(self.confb.packages[removed_key][removed_conf].export_dict(forjson=True))
        expected = '{"newpackages": {}, "oldpackages": {}, "newconfigs": '
        expected += '{"' + removed_conf + '": {"value": ' + configJsonString + ', "package": "' + removed_key + '"}}'
        expected += ', "oldconfigs": {}, "newOptions": {}, "oldOptions": {}, "chaOptions": {}}'
        self.assertEqual(json.loads(jsonExport), json.loads(expected))
        importTest = Diff()
        importTest.importJson(jsonExport)
        self.assertEqual(importTest, result)

        result.apply(self.confa)
        self.assertEqual(self.confa, self.confb)
        result.revert(self.confa)
        self.assertEqual(self.confa.diff(self.confb), result)

    def test_missing_config_in_newconf(self):
        removed_key = list(self.confa.packages.keys())[0]
        removed_conf = list(self.confa.packages[removed_key].keys())[0]
        self.confb.packages[removed_key].pop(removed_conf)
        result = self.confa.diff(self.confb)
        self.assertEqual(result['newpackages'], {})
        self.assertEqual(result['newconfigs'], {})
        self.assertEqual(result['oldpackages'], {})
        self.assertEqual(result['oldconfigs'], {(removed_key, removed_conf): self.confa.packages[removed_key] [removed_conf]})
        self.assertEqual(result['newOptions'], {})
        self.assertEqual(result['oldOptions'], {})
        self.assertEqual(result['chaOptions'], {})

        jsonExport = result.exportJson()
        configJsonString = json.dumps(self.confa.packages[removed_key][removed_conf].export_dict(forjson=True))
        expected = '{"newpackages": {}, "oldpackages": {}, "newconfigs": {}, "oldconfigs": '
        expected += '{"' + removed_conf + '": {"value": ' + configJsonString + ', "package": "' + removed_key + '"}}'
        expected += ', "newOptions": {}, "oldOptions": {}, "chaOptions": {}}'
        self.assertEqual(json.loads(jsonExport), json.loads(expected))
        importTest = Diff()
        importTest.importJson(jsonExport)
        self.assertEqual(importTest, result)

        result.apply(self.confa)
        self.assertEqual(self.confa, self.confb)
        result.revert(self.confa)
        self.assertEqual(self.confa.diff(self.confb), result)

    def test_missing_option_in_oldconf(self):
        removed_key = list(self.confa.packages.keys())[0]
        removed_conf = list(self.confa.packages[removed_key].keys())[0]
        removed_option = \
            list(self.confa.packages[removed_key][removed_conf].keys.keys())[0]
        removed_option_dict = dict()
        removed_option_dict[(removed_key, removed_conf, removed_option)] = \
            self.confa.packages[removed_key][removed_conf].keys.pop(removed_option)
        result = self.confa.diff(self.confb)
        self.assertEqual(result['newpackages'], {})
        self.assertEqual(result['newconfigs'], {})
        self.assertEqual(result['oldpackages'], {})
        self.assertEqual(result['oldconfigs'], {})
        self.assertEqual(result['oldOptions'], {})
        self.assertEqual(result['chaOptions'], {})
        self.assertEqual(result['newOptions'], removed_option_dict)

        jsonExport = result.exportJson()
        removedOptVal = removed_option_dict[(removed_key, removed_conf, removed_option)]
        expected = '{"newpackages": {}, "oldpackages": {}, "newconfigs": {}, "oldconfigs": {}, "newOptions": {"'
        expected += removed_option+ '": {"value": "' + removedOptVal + '", "package": "' + removed_key + '", "config": "' + removed_conf + '"'
        expected += '}}, "oldOptions": {}, "chaOptions": {}}'
        self.assertEqual(json.loads(jsonExport), json.loads(expected))
        importTest = Diff()
        importTest.importJson(jsonExport)
        self.assertEqual(importTest, result)

        result.apply(self.confa)
        self.assertEqual(self.confa, self.confb)
        result.revert(self.confa)
        self.assertEqual(self.confa.diff(self.confb), result)

    def test_missing_option_in_newconf(self):
        removed_key = list(self.confa.packages.keys())[0]
        removed_conf = list(self.confa.packages[removed_key].keys())[0]
        removed_option = \
            list(self.confa.packages[removed_key][removed_conf].keys.keys())[0]
        removed_option_dict = dict()
        removed_option_dict[(removed_key, removed_conf, removed_option)] = \
                self.confb.packages[removed_key][removed_conf].keys.pop(removed_option)
        result = self.confa.diff(self.confb)
        self.assertEqual(result['newpackages'], {})
        self.assertEqual(result['newconfigs'], {})
        self.assertEqual(result['oldpackages'], {})
        self.assertEqual(result['oldconfigs'], {})
        self.assertEqual(result['newOptions'], {})
        self.assertEqual(result['chaOptions'], {})
        self.assertEqual(result['oldOptions'], removed_option_dict)

        jsonExport = result.exportJson()
        removedOptVal = removed_option_dict[(removed_key, removed_conf, removed_option)]
        expected = '{"newpackages": {}, "oldpackages": {}, "newconfigs": {}, "oldconfigs": {}, "newOptions": {}, "oldOptions": {"'
        expected += removed_option+ '": {"value": "' + removedOptVal + '", "package": "' + removed_key + '", "config": "' + removed_conf + '"'
        expected += '}}, "chaOptions": {}}'
        self.assertEqual(json.loads(jsonExport), json.loads(expected))
        importTest = Diff()
        importTest.importJson(jsonExport)
        self.assertEqual(importTest, result)

        result.apply(self.confa)
        self.assertEqual(self.confa, self.confb)
        result.revert(self.confa)
        self.assertEqual(self.confa.diff(self.confb), result)

    def test_changed_option_in_newconf(self):
        removed_key = list(self.confa.packages.keys())[0]
        removed_conf = list(self.confa.packages[removed_key].keys())[0]
        removed_option = \
            list(self.confa.packages[removed_key][removed_conf].keys.keys())[0]
        removed_option_dict = dict()
        removed_option_dict[(removed_key, removed_conf, removed_option)] = \
            (self.confa.packages[removed_key][removed_conf].keys.get(removed_option),\
            str(self.confa.packages[removed_key][removed_conf].keys.get(removed_option))\
            + 'changed')
        self.confb.packages[removed_key][removed_conf].keys[removed_option] = \
            str(self.confa.packages[removed_key][removed_conf].keys.get(removed_option))\
            + 'changed'
        result = self.confa.diff(self.confb)
        self.assertEqual(result['newpackages'], {})
        self.assertEqual(result['newconfigs'], {})
        self.assertEqual(result['oldpackages'], {})
        self.assertEqual(result['oldconfigs'], {})
        self.assertEqual(result['newOptions'], {})
        self.assertEqual(result['oldOptions'], {})
        self.assertEqual(result['chaOptions'], removed_option_dict)

        jsonExport = result.exportJson()
        removedOptVal = removed_option_dict[(removed_key, removed_conf, removed_option)]
        expected = '{"newpackages": {}, "oldpackages": {}, "newconfigs": {}, "oldconfigs": {}, "newOptions": {}, "oldOptions": {}, "chaOptions": {"'
        expected += removed_option + '": {"value": ' + json.dumps(removedOptVal) + ', "package": "' + removed_key + '", "config": "' + removed_conf + '"'
        expected += '}}}'
        self.assertEqual(json.loads(jsonExport), json.loads(expected))
        importTest = Diff()
        importTest.importJson(jsonExport)
        self.assertEqual(importTest, result)

        result.apply(self.confa)
        self.assertEqual(self.confa, self.confb)
        result.revert(self.confa)
        self.assertEqual(self.confa.diff(self.confb), result)
