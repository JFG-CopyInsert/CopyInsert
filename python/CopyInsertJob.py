# -*- coding: utf-8 -*-
# Job that runs CopyInsertLib.CopyInsert.EnableMenu each time a document view
# is created (event OnViewCreated). It replaces the Events.xcu binding, so no
# entry appears in Tools > Customize > Events.
import uno
import unohelper
from com.sun.star.task import XJob

IMPL_NAME = "org.libreoffice.extension.copyinsert.EnableMenuJob"
MACRO_URL = ("vnd.sun.star.script:CopyInsertLib.CopyInsert.EnableMenu"
             "?language=Basic&location=application")


class EnableMenuJob(unohelper.Base, XJob):
    def __init__(self, ctx):
        self.ctx = ctx

    def execute(self, args):
        try:
            mspf = self.ctx.getValueByName(
                "/singletons/com.sun.star.script.provider.theMasterScriptProviderFactory")
            script = mspf.createScriptProvider("").getScript(MACRO_URL)
            script.invoke((), (), ())
        except Exception:
            pass    # never disturb the opening of a document
        return None


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    EnableMenuJob, IMPL_NAME, ("com.sun.star.task.Job",))
