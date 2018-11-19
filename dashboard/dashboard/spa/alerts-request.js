/* Copyright 2018 The Chromium Authors. All rights reserved.
   Use of this source code is governed by a BSD-style license that can be
   found in the LICENSE file.
*/
'use strict';
tr.exportTo('cp', () => {
  class AlertsRequest extends cp.RequestBase {
    constructor(options) {
      super(options);
      this.method_ = 'POST';
      this.body_ = new FormData();
      for (const [key, value] of Object.entries(options.body)) {
        this.body_.set(key, value);
      }
    }

    get url_() {
      return '/api/alerts';
    }

    async localhostResponse_() {
      const improvements = Boolean(this.improvements);
      const alerts = [];
      const measurements = [
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
      ];
      const testCases = [
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
      ];
      for (let i = 0; i < 10; ++i) {
        const revs = new tr.b.math.Range();
        revs.addValue(parseInt(1e6 * Math.random()));
        revs.addValue(parseInt(1e6 * Math.random()));
        let bugId = undefined;
        if (this.bugId !== '' && (Math.random() > 0.5)) {
          if (Math.random() > 0.5) {
            bugId = -1;
          } else {
            bugId = 123456;
          }
        }
        alerts.push({
          bot: 'bot' + (i % 3),
          bug_components: [],
          bug_id: bugId,
          bug_labels: [],
          descriptor: {
            bot: 'master:bot' + (i * 3),
            measurement: measurements[i],
            statistic: 'avg',
            testCase: testCases[i % testCases.length],
            testSuite: 'system_health.common_desktop',
          },
          end_revision: revs.max,
          improvement: improvements && (Math.random() > 0.5),
          key: tr.b.GUID.allocateSimple(),
          master: 'master',
          median_after_anomaly: 100 * Math.random(),
          median_before_anomaly: 100 * Math.random(),
          start_revision: revs.min,
          test: measurements[i] + '/' + testCases[i % testCases.length],
          units: measurements[i].startsWith('memory') ? 'sizeInBytes' : 'ms',
        });
      }
      alerts.sort((x, y) => x.start_revision - y.start_revision);
      return {
        anomalies: alerts,
      };
    }
  }

  return {AlertsRequest};
});
