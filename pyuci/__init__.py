""" uci parsing """

import logging
import re
import json


class UciError(RuntimeError):
    pass

class UciWrongTypeError(UciError):
    pass

class UciNotFoundError(UciError):
    pass

class UciParseError(UciError):
    pass

class Diff(dict):
    """ class providing diffs on Config objects """

    def __init__(self):
        """ initialize instance """
        self['newpackages'] = {}
        self['newconfigs'] = {}
        self['oldpackages'] = {}
        self['oldconfigs'] = {}
        self['newOptions'] = {}
        self['oldOptions'] = {}
        self['chaOptions'] = {}

    def importJson(self, jsonString):
        """ generate diff object from a json string """
        importDict = json.loads(jsonString)
        
        self.importPackage(importDict['newpackages'], 'newpackages')
        self.importPackage(importDict['oldpackages'], 'oldpackages')

        self.importConfig(importDict['newconfigs'], 'newconfigs')
        self.importConfig(importDict['oldconfigs'], 'oldconfigs')

        self.importOptions(importDict['newOptions'], 'newOptions')
        self.importOptions(importDict['oldOptions'], 'oldOptions')
        self.importOptions(importDict['chaOptions'], 'chaOptions')

    def importPackage(self, packageDict, importTo):
        for packageName, package in packageDict.items():
            curPackage = Package(packageName)
            curPackage.importDictFromJson(package)
            self[importTo][packageName] = curPackage

    def importConfig(self, confDict, importTo):
        for confName, confData in confDict.items():
            indexTuple = (confData['package'], confName)
            confValue = confData['value']
            config = Config(confValue.pop('.type'), confValue.pop('.name'), confValue.pop(".anonymous"))
            config.keys = confValue
            self[importTo][indexTuple] = config

    def importOptions(self, optDict, importTo):
        for optName, optData in optDict.items():
            indexTuple = (optData['package'], optData['config'], optName)

            # if it is a changed option treat values as a tuple (there is no tuple in json!)
            if importTo == 'chaOptions':
                self[importTo][indexTuple] = (optData['value'][0], optData['value'][1])
            else:
                self[importTo][indexTuple] = optData['value']

    def exportJson(self):
        """ export diff object to a json string """
        export = {}
        export['newpackages'] = {}
        export['oldpackages'] = {}

        for packageName, package in self['newpackages'].items():
            export['newpackages'][packageName] = package.exportDictForJson()

        for packageName, package in self['oldpackages'].items():
            export['oldpackages'][packageName] = package.exportDictForJson()

        export['newconfigs'] = self.exportConfigJson(self['newconfigs'])
        export['oldconfigs'] = self.exportConfigJson(self['oldconfigs'])

        export['newOptions'] = self.exportOptions(self['newOptions'])
        export['oldOptions'] = self.exportOptions(self['oldOptions'])
        export['chaOptions'] = self.exportOptions(self['chaOptions'])

        return json.dumps(export)

    def exportConfigJson(self, confDict):
        export = {}
        for confIndex, config in confDict.items():
            packageName = confIndex[0]
            configName = confIndex[1]
            export[configName] = {}
            export[configName]['value'] = config.export_dict(forjson=True)
            export[configName]['package'] = packageName
        return export

    def exportOptions(self, optDict):
        export = {}
        for optIndex, value in optDict.items():
            packageName = optIndex[0]
            configName = optIndex[1]
            optionName = optIndex[2]
            export[optionName] = {}
            export[optionName]['value'] = value
            export[optionName]['package'] = packageName
            export[optionName]['config'] = configName
        return export

    def diff(self, UciOld, UciNew):
        """ generate a diff between UciOld and UciNew """
        # find new package keys
        for key in UciNew.packages.keys():
            if not (key in UciOld.packages.keys()):
                self['newpackages'][key] = UciNew.packages[key]
            else:
                oldPackage = UciOld.packages[key]
                newPackage = UciNew.packages[key]

                self.diffPackage(oldPackage, newPackage)

        # find old packages and configs
        for packageName, package in UciOld.packages.items():
            if not (packageName in UciNew.packages.keys()):
                self['oldpackages'][packageName] = package
            else:
                newPackage = UciNew.packages[packageName]
                for confName, conf in package.items():
                    if not (confName in newPackage.keys()):
                        self['oldconfigs'][(packageName, confName)] = conf

        return self

    def diffPackage(self, oldPackage, newPackage):
        """ generate a diff between oldPackage and newPackage """
        for confkey in newPackage.keys():
            if not (confkey in oldPackage.keys()):
                indexTuple = (newPackage.name, confkey)
                self['newconfigs'][indexTuple] = newPackage[confkey]
            else:
                oldConfig = oldPackage[confkey]
                newConfig = newPackage[confkey]
                packageName = newPackage.name

                self.diffConfig(oldConfig, newConfig, packageName)

    def diffConfig(self, oldConfig, newConfig, packageName):
        """ diff two configurations """
        newOptions = newConfig.export_dict(forjson=True)
        oldOptions = oldConfig.export_dict(forjson=True)

        for option_key, option_value in newOptions.items():
            indexTuple = (packageName, newConfig.name, option_key)

            if not (option_key in oldOptions.keys()):
                self['newOptions'][indexTuple] = option_value
            else:
                if option_value != oldOptions[option_key]:
                    optionTuple = (oldOptions[option_key], option_value)
                    self['chaOptions'][indexTuple] = optionTuple

        for option_key, option_value in oldOptions.items():
            indexTuple = (packageName, newConfig.name, option_key)
            if not (option_key in newOptions.keys()):
                self['oldOptions'][indexTuple] = option_value

    def apply(self, toUci):
        """ applys a diff to a Uci-Config """
        for packageName, package in self['newpackages'].items():
            toUci.add_package(packageName, package)

        for configIndex, config in self['newconfigs'].items():
            toUci.add_config(configIndex[0], config)

        for packageName, package in self['oldpackages'].items():
            toUci.del_package(packageName)

        for configIndex, config in self['oldconfigs'].items():
            toUci.del_config(configIndex[0], config)

        for optIndex, opt in self['newOptions'].items():
            toUci.packages[optIndex[0]][optIndex[1]].set_option(optIndex[2], opt)

        for optIndex, opt in self['oldOptions'].items():
            toUci.packages[optIndex[0]][optIndex[1]].remove_option(optIndex[2])

        for optIndex, opt in self['chaOptions'].items():
            toUci.packages[optIndex[0]][optIndex[1]].set_option(optIndex[2], opt[1])

    def revert(self, toUci):
        """ reverts a diff from a Uci-Config """
        for packageName, package in self['newpackages'].items():
            toUci.del_package(packageName)

        for configIndex, config in self['newconfigs'].items():
            toUci.del_config(configIndex[0], config)

        for packageName, package in self['oldpackages'].items():
            toUci.add_package(packageName, package)

        for configIndex, config in self['oldconfigs'].items():
            toUci.add_config(configIndex[0], config)

        for optIndex, opt in self['newOptions'].items():
            toUci.packages[optIndex[0]][optIndex[1]].remove_option(optIndex[2])

        for optIndex, opt in self['oldOptions'].items():
            toUci.packages[optIndex[0]][optIndex[1]].set_option(optIndex[2], opt)

        for optIndex, opt in self['chaOptions'].items():
            toUci.packages[optIndex[0]][optIndex[1]].set_option(optIndex[2], opt[0])

class Config(object):
    def __init__(self, uci_type, name, anon):
        self.uci_type = uci_type
        self.name = name
        self.anon = anon
        # options are key -> str(value)
        # lists are key -> [value x, value y]
        self.keys = {}

    def add_list(self, key, value):
        if key in self.keys:
            self.keys[key].append(value)
        else:
            self.keys[key] = [value]

    def remove_list_pos(self, key, pos):
        try:
            if not isinstance(self.keys[key], list):
                raise UciWrongTypeError
            del self.keys[key][pos]
        except(ValueError, KeyError):
            return

    def remove_list_value(self, key, value):
        try:
            self.keys[key].remove(value)
        except(ValueError, KeyError):
            return

    def set_option(self, key, value):
        self.keys[key] = value

    def remove_option(self, key):
        if key in self.keys:
            del self.keys[key]

    def export_uci(self):
        export = []
        if not self.anon:
            export.append("config '%s' '%s'\n" % (self.uci_type, self.name))
        else:
            export.append("config '%s'\n" % (self.uci_type))
        for opt_list in self.keys:
            if isinstance(self.keys[opt_list], list):
                export.extend([("\tlist '%s' '%s'\n" % (opt_list, element)) for element in self.keys[opt_list]])
            else:
                export.append("\toption '%s' '%s'\n" % (opt_list, self.keys[opt_list]))
        export.append('\n')
        return ''.join(export)

    def export_dict(self, forjson = False, foradd = False):
        export = {}
        export_keys = self.keys
        if forjson:
            export['.name']  = self.name
            export['.type']  = self.uci_type
            export['.anonymous'] = self.anon
            for i,j in export_keys.items():
                export[i] = j
        elif foradd:
            export['name']    = self.name
            export['type']    = self.uci_type
            export['values']  = export_keys
        else:
            export['section'] = self.name
            export['type']    = self.uci_type
            export['values']  = export_keys
        return export

    def __repr__(self):
        return "Config[%s:%s] %s" % (self.uci_type, self.name, repr(self.keys))

    def __eq__(self, other):
        isEqual = True
        isEqual = isEqual and (self.name == other.name)
        isEqual = isEqual and (self.anon == other.anon)
        isEqual = isEqual and (self.keys == other.keys)

        return isEqual

class Package(dict):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def add_config(self, config):
        self[config.name] = config

    def del_config(self, config):
        self.pop(config.name)

    def add_config_json(self, config):
        cur_config = Config(config.pop('.type'), config.pop('.name'), config.pop(".anonymous"))
        cur_config.keys = config
        self.add_config(cur_config)
        return cur_config
    
    def exportDictForJson(self):
        export={}
        export['values'] = {}
        for configname, config in self.items():
            export['values'][config.name] =\
                config.export_dict(forjson=True)
        return export

    def importDictFromJson(self, confDict):
        for confName, conf in confDict['values'].items():
            self.add_config_json(conf)

    def __eq__(self, other):
        isEqual = True
        isEqual = isEqual and (self.name == other.name)
        isEqual = isEqual and super().__eq__(other)

        return isEqual

class Uci(object):
    logger = logging.getLogger('uci')
    def __init__(self):
        self.packages = {}

    def add_package(self, package_name, package=None):
        if package_name not in self.packages:
            if not package:
                self.packages[package_name] = Package(package_name)
            else:
                self.packages[package_name] = package
        return self.packages[package_name]

    def add_config(self, package_name, config):
        if not isinstance(config, Config):
            return RuntimeError()
        if package_name not in self.packages:
            self.packages[package_name] = Package()
        self.packages[package_name].add_config(config)

    def del_config(self, package_name, config):
        if package_name not in self.packages:
            raise RuntimeError()
        self.packages[package_name].del_config(config)

    def del_package(self, package_name):
        if package_name not in self.packages:
            raise RuntimeError()
        self.packages.pop(package_name)

    def del_path(self, path):
        pass

    def export_uci_tree(self):
        export = []
        for package, content in self.packages.items():
            export.append("package '%s'\n" % package)
            export.append("\n")
            export.extend([config.export_uci() for configname, config in content.items()])
        return "".join(export)

    def diff(self, new):
        return Diff().diff(self, new)

    def load_tree(self, export_tree_string):
        cur_package = None
        config = None

        export_tree = json.loads(export_tree_string)

        for package in export_tree.keys():
            cur_package = self.add_package(package)
            for config in export_tree[package]['values']:
                config = export_tree[package]['values'][config]
                cur_package.add_config_json(config)

    def export_json(self):
        export={}
        for packagename, package in self.packages.items():
            export[packagename] = {}
            export[packagename]['values'] = {}
            for configname, config in package.items():
                export[packagename]['values'][config.name] =\
                    config.export_dict(forjson=True)
        return json.dumps(export)

    def __eq__(self, other):
        return self.packages == other.packages


class UciConfig(object):
    """ Class for configurations - like network... """
    pass

if __name__ == '__main__':
    uci_export = open('uci_export')
    alles = uci_export.read(1000000)
    logging.basicConfig()
    ucilog = logging.getLogger('uci')
    ucilog.setLevel(logging.DEBUG)
    uci = Uci()
    uci.load_tree(alles)
    print(uci.export_tree())
