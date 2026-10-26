#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.xdo: Backwards-compatible wrapper for flktux.engine.emitter
"""

from .engine.emitter import XdoEmitter, EMITTER as XDO

XdoPipe = XdoEmitter

__all__ = ["XdoPipe", "XDO"]
