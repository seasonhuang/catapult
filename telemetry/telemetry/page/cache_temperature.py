# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Cache temperature specifies how the browser cache should be configured before
the page run.

See design doc for details:
https://docs.google.com/document/u/1/d/12D7tkhZi887g9d0U2askU9JypU_wYiEI7Lw0bfwxUgA
"""

import logging
from telemetry.core import exceptions

# Default Cache Temperature. The page doesn't care which browser cache state
# it is run on.
ANY = 'any'
# Emulates cold runs. Clears various caches and data with using tab.ClearCache()
# and tab.ClearDataForOrigin().
COLD = 'cold'
# Emulates warm browser runs. Ensures that the page was visited once in a
# different renderer.
WARM_BROWSER = 'warm-browser'
# Emulates hot runs. Ensures that the page was visited at least twice in a
# different renderer before the run.
HOT_BROWSER = 'hot-browser'
# Emulates warm renderer runs. Ensures that the page was visited once before the
# run in the same renderer.
WARM = 'warm-renderer'
# Emulates hot renderer runs. Ensures that the page was visited at least twice
# in the same renderer before the run.
HOT = 'hot-renderer'


class _MarkTelemetryInternal(object):
  def __init__(self, tab, identifier):
    self.tab = tab
    self.identifier = identifier

  def __enter__(self):
    # This marker must match the regexp in
    # ChromeProcessHelper.findTelemetryInternalRanges_().
    marker = 'telemetry.internal.%s.start' % self.identifier
    self.tab.ExecuteJavaScript("console.time({{ marker }});", marker=marker)
    self.tab.ExecuteJavaScript("console.timeEnd({{ marker }});", marker=marker)
    return self

  def __exit__(self, exception_type, exception_value, traceback):
    if exception_type:
      return True
    # This marker must match the regexp in
    # ChromeProcessHelper.findTelemetryInternalRanges_().
    marker = 'telemetry.internal.%s.end' % self.identifier
    self.tab.ExecuteJavaScript("console.time({{ marker }});", marker=marker)
    self.tab.ExecuteJavaScript("console.timeEnd({{ marker }});", marker=marker)
    return True


def _ClearCacheAndData(tab, url):
  tab.ClearCache(force=True)
  tab.ClearDataForOrigin(url)

def _WarmCache(page, tab, temperature):
  with _MarkTelemetryInternal(tab, 'warm_cache.%s' % temperature):
    page.RunNavigateSteps(tab.action_runner)
    page.RunPageInteractions(tab.action_runner)
    tab.Navigate("about:blank")
    tab.WaitForDocumentReadyStateToBeComplete()
    # Stop service worker after each cache warming to ensure service worker
    # script evaluation will be executed again in next navigation.
    tab.StopAllServiceWorkers()


class CacheManipulator(object):
  RENDERER_TEMPERATURE = None
  BROWSER_TEMPERATURE = None
  @staticmethod
  def PrepareRendererCache(page, tab, previous_page):
    raise NotImplementedError

  @classmethod
  def PrepareBrowserCache(cls, page, browser, previous_page):
    # Perform browser cache manipulation in a different tab.
    tab = browser.tabs.New()
    cls.PrepareRendererCache(page, tab, previous_page)
    tab.Close()


class AnyCacheManipulator(CacheManipulator):
  RENDERER_TEMPERATURE = ANY
  BROWSER_TEMPERATURE = None
  @staticmethod
  def PrepareRendererCache(page, tab, previous_page):
    pass

  @classmethod
  def PrepareBrowserCache(cls, page, browser, previous_page):
    raise exceptions.Error('Prepare browser cache not supported')


class ColdCacheManipulator(CacheManipulator):
  RENDERER_TEMPERATURE = COLD
  BROWSER_TEMPERATURE = None
  @staticmethod
  def PrepareRendererCache(page, tab, previous_page):
    if previous_page is None:
      # DiskCache initialization is performed asynchronously on Chrome start-up.
      # Ensure that DiskCache is initialized before starting the measurement to
      # avoid performance skew.
      # This is done by navigating to an inexistent URL and then wait for the
      # navigation to complete.
      # TODO(kouhei) Consider moving this logic to PageCyclerStory
      with _MarkTelemetryInternal(tab, 'ensure_diskcache'):
        tab.Navigate("http://does.not.exist")
        tab.WaitForDocumentReadyStateToBeComplete()
    _ClearCacheAndData(tab, page.url)

  @classmethod
  def PrepareBrowserCache(cls, page, browser, previous_page):
    raise exceptions.Error('Prepare browser cache not supported')


class WarmCacheManipulator(CacheManipulator):
  RENDERER_TEMPERATURE = WARM
  BROWSER_TEMPERATURE = WARM_BROWSER
  @staticmethod
  def PrepareRendererCache(page, tab, previous_page):
    if (previous_page is not None and
        previous_page.url == page.url and
        previous_page.cache_temperature == COLD):
      if '#' in page.url:
        # TODO(crbug.com/768780): Move this operation to tab.Navigate().
        # This navigates to inexistent URL to avoid in-page hash navigation.
        # Note: Unlike PCv1, PCv2 iterates the same URL for different cache
        #       configurations. This may issue blink in-page hash navigations,
        #       which isn't intended here.
        with _MarkTelemetryInternal(tab, 'avoid_double_hash_navigation'):
          tab.Navigate("http://does.not.exist")
          tab.WaitForDocumentReadyStateToBeComplete()
      # Stop all service workers before running tests to measure the starting
      # time of service worker too.
      tab.StopAllServiceWorkers()
    else:
      _ClearCacheAndData(tab, page.url)
      _WarmCache(page, tab, 'warm')


class HotCacheManipulator(CacheManipulator):
  RENDERER_TEMPERATURE = HOT
  BROWSER_TEMPERATURE = HOT_BROWSER
  @staticmethod
  def PrepareRendererCache(page, tab, previous_page):
    if (previous_page is not None and
        previous_page.url == page.url and
        previous_page.cache_temperature != ANY):
      if previous_page.cache_temperature == COLD:
        _WarmCache(page, tab, HOT)
      else:
        if '#' in page.url:
          # TODO(crbug.com/768780): Move this operation to tab.Navigate().
          # This navigates to inexistent URL to avoid in-page hash navigation.
          # Note: Unlike PCv1, PCv2 iterates the same URL for different cache
          #       configurations. This may issue blink in-page hash navigations,
          #       which isn't intended here.
          with _MarkTelemetryInternal(tab, 'avoid_double_hash_navigation'):
            tab.Navigate("http://does.not.exist")
            tab.WaitForDocumentReadyStateToBeComplete()
        # Stop all service workers before running tests to measure the starting
        # time of service worker too.
        tab.StopAllServiceWorkers()

    else:
      _ClearCacheAndData(tab, page.url)
      _WarmCache(page, tab, 'warm')
      _WarmCache(page, tab, 'hot')


def EnsurePageCacheTemperature(page, browser, previous_page=None):
  temperature = page.cache_temperature
  logging.info('PageCacheTemperature: %s', temperature)
  for c in [AnyCacheManipulator, ColdCacheManipulator, WarmCacheManipulator,
            HotCacheManipulator]:
    if temperature == c.RENDERER_TEMPERATURE:
      c.PrepareRendererCache(page, browser.tabs[0], previous_page)
      return
    elif temperature == c.BROWSER_TEMPERATURE:
      c.PrepareBrowserCache(page, browser, previous_page)
      return
  raise NotImplementedError('Unrecognized cache temperature: %s' % temperature)
