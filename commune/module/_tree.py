
from typing import *
import os
from copy import deepcopy

class Tree:
    tree_cache = {} # cache for tree

    # def __init__(self, **kwargs):
    #     self.set_config(kwargs=locals())
    #     # cls.thread(self.run_loop)
    
    @classmethod
    def resolve_extension(cls, filename:str, extension = '.py') -> str:
        if filename.endswith(extension):
             return filename
        return filename + extension

    @classmethod
    def simple2path(cls, 
                    simple_path:str,
                    tree = None,
                    extension = '.py',
                    verbose = False,
                    **kwargs) -> bool:
        """
        converts the module path to a file path

        for example 

        model.openai.gpt3 -> model/openai/gpt3.py, model/openai/gpt3_module.py, model/openai/__init__.py 
        model.openai -> model/openai.py or model/openai_module.py or model/__init__.py

        Parameters:
            path (str): The module path
        """
        if cls.can_import_object(simple_path):
            return simple_path
        if simple_path.endswith(extension):
            simple_path = simple_path[:-len(extension)]

        path = None
        dir_paths = list(set([cls.pwd(), cls.root_path + '/module', cls.root_path + '/modules',  cls.root_path  ]))

        for dir_path in dir_paths:
            # '/' count how many times the path has been split
            module_dirpath = dir_path + '/' + simple_path.replace('.', '/')
            module_filepath = dir_path + '/' + cls.resolve_extension(simple_path.replace('.', '/'))
            is_module_dir = os.path.isdir(module_dirpath)
            is_module_file = os.path.isfile(module_filepath)

            if is_module_file:
                path = module_filepath
            elif is_module_dir:
                simple_path_filename = simple_path.replace('.', '_')
                filename_options = [cls.resolve_extension(f)  for f in [simple_path_filename, simple_path_filename + '_module', 'module_'+ simple_path_filename] + ['module', 'main'] + simple_path.split('.')]  
                paths_in_dir = os.listdir(module_dirpath)
                for p in paths_in_dir:
                    if p.split('/')[-1] in filename_options:
                        new_path = module_dirpath + '/' + p
                        if os.path.isfile(new_path):
                            path = new_path
                            break   
 

                
            if path != None:
                break

        if path == None:
            tree = cls.tree()
            is_in_tree = bool(simple_path in tree)
            if not  is_in_tree:
                cls.print(f'Path not found in tree: {simple_path}', color='red', verbose=verbose )
                tree = cls.tree(update=False, include_root=True)
            if simple_path in tree:
                path = tree[simple_path]
        assert path != None, f'Path not found for simple path {simple_path}'

        return path
    
    def path2tree(self, **kwargs) -> str:
        trees = self.trees()
        path2tree = {}
        for tree in trees:
            for module, path in self.tree(tree).items():
                path2tree[path] = tree
        return path2tree
    
    @classmethod
    def root_tree(cls, **kwargs):
        return cls.tree(path = cls.libpath, include_root=False, **kwargs)

    @classmethod
    def is_repo(cls, libpath:str ):
        # has the .git folder
        return bool([f for f in cls.ls(libpath) if '.git' in f and os.path.isdir(f)])
    
    @classmethod
    def default_tree_path(cls):
        return cls.libpath
    
    
    @classmethod
    def tree(cls, 
                path = None,
                search=None,
                update = False,
                max_age = None, 
                include_root = False,
                verbose = False,
                cache = True,
                save = True,
                **kwargs
                ) -> List[str]:
        tree = {}
        mode = None
        timestamp = cls.time()

        path = os.path.abspath(path or cls.default_tree_path())
        cache_path = path.split('/')[-1]
        # the tree is cached in memory to avoid repeated reads from storage
        # if the tree is in the cache and the max_age is not None, we want to check the age of the cache
        use_tree_cache = bool(cache and cache_path in cls.tree_cache) and not update
        if use_tree_cache:
            tree_data = cls.tree_cache[cache_path]
            assert all([k in tree_data for k in ['data', 'timestamp']]), 'Invalid tree cache'
            cache_age = timestamp - tree_data['timestamp']
            if max_age != None and cache_age < max_age:
                tree = tree_data['data']
                assert isinstance(tree, dict), 'Invalid tree data'
                mode = 'memory_cache'

        if len(tree) == 0:
            # if the tree is not cached in memory or we want to check the storage cache
            tree =  cls.get(cache_path, {}, max_age=max_age, update=update)
            mode = 'storage_cache'
            if len(tree) == 0 :
                # if the tree is not in the storage cache, we want to build it and store it
                mode = 'build'
                tree = cls.build_tree(path)
                cls.tree_cache[cache_path] = {'data': tree, 'timestamp': timestamp}
                if save: # we want to save the tree to storage
                    cls.put(cache_path, tree)
        
        assert mode != None, 'Invalid mode'
        if search != None:
            tree = {k:v for k,v in tree.items() if search in k}
        if include_root:
            tree = {**tree, **cls.root_tree()}
        
        if verbose:
            latency = cls.time() - timestamp
            cls.print(f'Tree  path={path} latency={latency}, n={len(tree)} mode={mode}', color='cyan')
        return tree
    
    
    @classmethod
    def local_tree(cls, **kwargs):
        return cls.build_tree(cls.pwd(), **kwargs)
    

    @classmethod
    def build_tree(cls,
                    tree_path:str = None, 
                    extension = '.py', 
                    verbose = True,
                    search=None,
                   **kwargs):
        
        tree_path = tree_path or cls.libpath
        t1 = cls.time()
        tree_path = cls.resolve_path(tree_path)
        module_tree = {}
        for path in cls.glob(tree_path+'/**/**.py', recursive=True):
            simple_path = cls.path2simple(path)
            if simple_path == None:
                continue
            module_tree[simple_path] = path
        latency = cls.time() - t1
        if search != None:
            module_tree = {k:v for k,v in module_tree.items() if search in k}
        cls.print(f'Tree updated -> path={tree_path} latency={latency}, n={len(module_tree)}',  color='cyan', verbose=verbose)

        return module_tree
    @classmethod
    def tree_paths(cls, update=False, **kwargs) -> List[str]:
        return cls.ls()
    
    @classmethod
    def tree_hash(cls, *args, **kwargs):
        tree = cls.tree(*args, **kwargs)
        tree_hash = cls.hash(tree)
        cls.put('tree_hash', tree_hash)
        return tree_hash

    @classmethod
    def old_tree_hash(cls, *args, **kwargs):
        return cls.get('tree_hash', None)

    @classmethod
    def has_tree_changed(cls, *args, **kwargs):
        old_tree_hash = cls.old_tree_hash(*args, **kwargs)
        new_tree_hash = cls.tree_hash(*args, **kwargs)
        return old_tree_hash != new_tree_hash

    def run_loop(self, *args, sleep_time=10, **kwargs):
        while True:
            self.print('Checking for tree changes')
            if self.has_tree_changed():
                self.tree(update=True)
            self.sleep(10)
        
    @classmethod
    def add_tree(cls, tree_path:str = './', **kwargs):
        return cls.tree(tree_path, update=True)
    
    @classmethod
    def rm_tree(cls, tree_path:str, **kwargs):
        return cls.rm(tree_path)
    
    @classmethod
    def rm_trees(cls, **kwargs):
        for tree_path in cls.tree_paths():
            cls.rm(tree_path)

    

    @classmethod
    def pwd_tree(cls):
        tree2path   =  cls.tree2path()
        pwd = cls.pwd()
        return {v:k for k,v in tree2path.items()}.get(pwd, None)

    @classmethod
    def is_pwd_tree(cls):
        return cls.pwd() == cls.libpath
    
    @classmethod
    def trees(cls):
        tree_paths = cls.tree_paths()
        trees = [t.split('/')[-1] for t in tree_paths]
        return trees

    @classmethod
    def tree2path(cls, tree : str = None, **kwargs) -> str:
        tree_paths = cls.tree_paths(**kwargs)
        tree2path = {t.split('/')[-1]: t for t in tree_paths}
        if tree != None:
            return tree2path[tree]
        return tree2path
    
    @classmethod
    def path2simple(cls,  
                    path:str, 
                    tree = None,  
                    ignore_prefixes = ['src', 'commune', 'modules', 'commune.modules', 'commune.module', 'module', 'router'],
                    module_folder_filnames = ['__init__', 'main', 'module'],
                    module_extension = 'py',
                    ignore_suffixes = ['module'],
                    name_map = {'commune': 'module'},
                    compress_path = True,
                    verbose = False,
                    num_lines_to_read = 100,
                    ) -> str:
        
        path  = os.path.abspath(path)
        path_filename_with_extension = path.split('/')[-1] # get the filename with extension     
        path_extension = path_filename_with_extension.split('.')[-1] # get the extension
        assert path_extension == module_extension, f'Invalid extension {path_extension} for path {path}'
        path_filename = path_filename_with_extension[:-len(path_extension)-1] # remove the extension
        path_filename_chunks = path_filename.split('_')
        path_chunks = path.split('/')
        # for instance model/openai/openai.py is a module folder where the filename is openai and the path is model/openai

        is_module_folder = all([bool(chunk in path_chunks) for chunk in path_filename_chunks])
        is_module_folder = is_module_folder or (path_filename in module_folder_filnames)
        
        if is_module_folder:
            path = '/'.join(path.split('/')[:-1])

        # STEP 2 REMOVE THE TREE PATH (IF IT EXISTS)
        # if the path is a module folder, we want to remove the folder name
        if path.startswith(cls.libpath):
            path = path[len(cls.libpath):]
        else:
            # if the tree path is not in the path, we want to remove the root path
            pwd = cls.pwd()
            path = path[len(pwd):]  

        if path.startswith('/'):
            path = path[1:]
        
        # strip the extension
        path = path.replace('/', '.')

        # remove the extension
        module_extension = '.'+module_extension
        if path.endswith(module_extension):
            path = path[:-len(module_extension)]

        if compress_path:
            # we want to remove redundant chunks 
            # for example if the path is 'module/module' we want to remove the redundant module
            path_chunks = path.split('.')
            simple_path = []
            for chunk in path_chunks:
                if chunk not in simple_path:
                    simple_path += [chunk]
            simple_path = '.'.join(simple_path)
        else:
            simple_path = path
        # remove prefixes from commune
        for prefix in ignore_prefixes:
            prefix += '.'
            if simple_path.startswith(prefix) and simple_path != prefix:
                simple_path = simple_path[len(prefix):]
                cls.print(f'Prefix {prefix} in path {simple_path}', color='yellow', verbose=verbose)

        for suffix in ignore_suffixes:
            suffix = '.' + suffix
            if simple_path.endswith(suffix) and simple_path != suffix:
                simple_path = simple_path[:-len(suffix)]
                cls.print(f'Suffix {prefix} in path {simple_path}', color='yellow', verbose=verbose)

        # remove leading and trailing dots
        if simple_path.startswith('.'):
            simple_path = simple_path[1:]
        if simple_path.endswith('.'):
            simple_path = simple_path[:-1]
        simple_path = name_map.get(simple_path, simple_path)
        return simple_path

    @classmethod
    def path_config_exists(cls, path:str,
                            config_files = ['config.yaml', 'config.yml'],
                              config_extensions=['.yaml', '.yml']) -> bool:
        '''
        Checks if the path exists
        '''
        config_files += [path.replace('.py', ext) for ext in config_extensions]
        dirpath = os.path.dirname(path)
        dir_files =  os.listdir(dirpath)
        if os.path.exists(dirpath) and any([[f.endswith(cf) for cf in config_files] for f in dir_files]):
            return True
        return False

    @classmethod
    def find_classes(cls, path):
        if os.path.isdir(path):
            path2classes = {}
            for p in cls.glob(path+'/**/**.py', recursive=True):
                path2classes[p] = cls.find_classes(p)
            return path2classes
        code = cls.get_text(path)
        classes = []
        for line in code.split('\n'):
            if all([s in line for s in ['class ', ':']]):
                new_class = line.split('class ')[-1].split('(')[0].strip()
                if new_class.endswith(':'):
                    new_class = new_class[:-1]
                if ' ' in new_class:
                    continue
                classes += [new_class]
        return [c for c in classes]
    
    @classmethod
    def find_object_paths(cls, path:str = './', **kwargs):
        classes = cls.find_classes(path)
        
        if isinstance(classes, dict):
            object_paths = []
            for p, c in classes.items():
                
                object_paths += [cls.path2simple(p) + '.' + c for c in classes[p]]
            return object_paths
        object_paths = [path + '.' + c for c in classes]
        return object_paths



    @classmethod
    def simple2objectpath(cls, 
                          simple_path:str,
                           cactch_exception = False, 
                           **kwargs) -> str:
        
        if cactch_exception:
            try:
                object_path = cls.simple2objectpath(simple_path, cactch_exception=False, **kwargs)
            except Exception as e:
                cls.print(f'Error in simple2objectpath: {cls.detailed_error(e)}', color='red')
                object_path = simple_path
            return object_path

        pwd = cls.pwd()
        object_path = cls.simple2path(simple_path, **kwargs)
        classes =  cls.find_classes(object_path)

        if object_path.startswith(cls.libpath):
            object_path = object_path[len(cls.libpath):]
        object_path = object_path.replace('.py', '')
        if object_path.startswith(pwd):
            object_path = object_path[len(pwd):]

        object_path = object_path.replace('/', '.')
        if object_path.startswith('.'):
            object_path = object_path[1:]
        print(object_path, classes)
        object_path = object_path + '.' + classes[-1]


        return object_path


    @classmethod
    def pwdtree(cls):
        tree2path   =  cls.tree2path()
        pwd = cls.pwd()
        return {v:k for k,v in tree2path.items()}.get(pwd, None)
    which_tree = pwdtree
    
    @classmethod
    def istree(cls):
        return cls.pwdtree() != None


    @classmethod
    def simple2object(cls, path:str, **kwargs) -> str:
        path =  cls.simple2objectpath(path, **kwargs)
        return cls.import_object(path)
    


    included_pwd_in_path = False
    @classmethod
    def import_module(cls, 
                      import_path:str, 
                      included_pwd_in_path=True, 
                      try_prefixes = ['commune', 'commune.modules', 'modules', 'commune.subspace', 'subspace']
                      ) -> 'Object':
        from importlib import import_module
        if included_pwd_in_path and not cls.included_pwd_in_path:
            import sys
            pwd = cls.pwd()
            sys.path.append(pwd)
            sys.path = list(set(sys.path))
            cls.included_pwd_in_path = True
        pwd = cls.pwd()
        try:
            return import_module(import_path)
        except Exception as _e:
            for prefix in try_prefixes:
                try:
                    return import_module(f'{prefix}.{import_path}')
                except Exception as e:
                    pass
            raise _e
    
    @classmethod
    def can_import_module(cls, module:str) -> bool:
        '''
        Returns true if the module is valid
        '''
        try:
            cls.import_module(module)
            return True
        except:
            return False
    @classmethod
    def can_import_object(cls, module:str) -> bool:
        '''
        Returns true if the module is valid
        '''
        try:
            cls.import_object(module)
            return True
        except:
            return False

    @classmethod
    def import_object(cls, key:str, verbose: bool = 0)-> Any:
        '''
        Import an object from a string with the format of {module_path}.{object}
        Examples: import_object("torch.nn"): imports nn from torch
        '''
        module = '.'.join(key.split('.')[:-1])
        object_name = key.split('.')[-1]
        if verbose:
            cls.print(f'Importing {object_name} from {module}')
        obj =  getattr(cls.import_module(module), object_name)
      
        return obj
    

    @classmethod
    def object_exists(cls, path:str, verbose=False)-> Any:
        try:
            cls.import_object(path, verbose=verbose)
            return True
        except Exception as e:
            return False
    
    imp = get_object = importobj = import_object

    @classmethod
    def module_exists(cls, module:str, **kwargs) -> bool:
        '''
        Returns true if the module exists
        '''
        return module in cls.modules(**kwargs)


    @classmethod
    def modules(cls, search=None, mode='local', tree='commune', **kwargs)-> List[str]:
        if any([str(k) in ['subspace', 's'] for k in [mode, search]]):
            module_list = cls.module('subspace')().modules(search=search, **kwargs)
        else:
            module_list = list(cls.tree(search=search, tree=tree, **kwargs).keys())
            if search != None:
                module_list = [m for m in module_list if search in m]
        return module_list

