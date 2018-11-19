/* Copyright 2018 The Chromium Authors. All rights reserved.
   Use of this source code is governed by a BSD-style license that can be
   found in the LICENSE file.
*/
'use strict';
tr.exportTo('cp', () => {
  class DescribeRequest extends cp.RequestBase {
    constructor(options) {
      super(options);
      this.method_ = 'POST';
      this.body_ = new FormData();
      this.body_.set('test_suite', options.testSuite);
    }

    get url_() {
      return '/api/describe';
    }

    async localhostResponse_() {
      return {
        measurements: [
          'memory:a_size',
          'memory:b_size',
          'memory:c_size',
          'cpu:a',
          'cpu:b',
          'cpu:c',
          'power',
          'loading',
          'startup',
          'size',
        ],
        bots: ['master:aaa', 'master:bbb', 'master:ccc'],
        cases: [
          'browse:media:facebook_photos',
          'browse:media:imgur',
          'browse:media:youtube',
          'browse:news:flipboard',
          'browse:news:hackernews',
          'browse:news:nytimes',
          'browse:social:facebook',
          'browse:social:twitter',
          'load:chrome:blank',
          'load:games:bubbles',
          'load:games:lazors',
          'load:games:spychase',
          'load:media:google_images',
          'load:media:imgur',
          'load:media:youtube',
          'search:portal:google',
        ],
      };
    }

    static mergeDescriptor(merged, descriptor) {
      for (const bot of descriptor.bots) merged.bots.add(bot);
      for (const measurement of descriptor.measurements) {
        merged.measurements.add(measurement);
      }
      for (const testCase of descriptor.cases) {
        merged.testCases.add(testCase);
      }
      for (const [tag, cases] of Object.entries(descriptor.caseTags || {})) {
        if (!merged.testCaseTags.has(tag)) {
          merged.testCaseTags.set(tag, new Set());
        }
        for (const testCase of cases) {
          merged.testCaseTags.get(tag).add(testCase);
        }
      }
    }
  }

  return {DescribeRequest};
});
