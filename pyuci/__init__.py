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

    def fromJson(self, jsonString):
        """ generate diff object from a json string """
        # TODO: not yet implemented
        pass

    def exportJson(self):
        """ export diff object to a json string """
        # TODO: not yet implemented
        pass

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
        if key in self.keys:
            if isinstance(self.keys[key], list):
                raise UciWrongTypeError()
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

class Package(dict):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def add_config(self, config):
        self[config.name] = config
    def add_config_json(self, config):
        anon = config.pop(".anonymous")
        cur_config = Config(config.pop('.type'), config.pop('.name'),anon=='true')
        self.add_config(cur_config)
        # TODO: find out if the following is still necessary
        for key in config.keys():
            if isinstance(config[key],str):
                try:
                    config[key] = config[key].replace("'",'"')
                    newval = json.loads(config[key])
                except ValueError:
                    newval = config[key]
                config[key] = newval
            cur_config.set_option(key,config[key])
        return cur_config

class Uci(object):
    logger = logging.getLogger('uci')
    def __init__(self):
        self.packages = {}

    def add_package(self, package_name):
        if package_name not in self.packages:
            self.packages[package_name] = Package(package_name)
        return self.packages[package_name]

    def add_config(self, package_name, config):
        if not isinstance(config, Config):
            return RuntimeError()
        if package_name not in self.packages:
            self.packages[package_name] = Package()
        self.packages[package_name].add_config(config)

    def del_config(self, config):
        pass

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
