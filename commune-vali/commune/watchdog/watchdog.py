import commune as c

class Watchdog(c.Module):
    def __init__(self, modules=['module', 'subspace']):
        self.modules = {m: c.module(m) for m in modules}
        c.thread(self.run_loop)

    def sync(self):
        self.modules = {m: c.module(m) for m in self.modules}
        max_age = 
        c.print('syncing...')
        c.ip(update=1)
        c.tree(update=1)
        c.namespace(update=1)
        c.print('synced')
        self.subspace = c.get_module('subspace')



    def run_loop(self,  sleep_time=30):
        while True:
            try:
                self.sync()
            except Exception as e:
                e = c.detailed_error(e)
                c.print(f'Error syncing, restarting {e}')
                
