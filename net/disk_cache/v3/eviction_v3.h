// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef NET_DISK_CACHE_EVICTION_H_
#define NET_DISK_CACHE_EVICTION_H_

#include "base/basictypes.h"
#include "base/memory/weak_ptr.h"
#include "net/disk_cache/disk_format.h"
#include "net/disk_cache/rankings.h"

namespace disk_cache {

class BackendImpl;
class EntryImpl;

// This class implements the eviction algorithm for the cache and it is tightly
// integrated with BackendImpl.
class Eviction {
 public:
  Eviction();
  ~Eviction();

  void Init(BackendImpl* backend);
  void Stop();

  // Deletes entries from the cache until the current size is below the limit.
  // If empty is true, the whole cache will be trimmed, regardless of being in
  // use.
  void TrimCache(bool empty);

  // Notifications of interesting events for a given entry.
  void OnOpenEntry(EntryImpl* entry);
  void OnCreateEntry(EntryImpl* entry);

  // Testing interface.
  void SetTestMode();
  void TrimDeletedList(bool empty);

 private:
  void PostDelayedTrim();
  void DelayedTrim();
  bool ShouldTrim();
  bool ShouldTrimDeleted();
  bool EvictEntry(CacheRankingsBlock* node, bool empty, Rankings::List list);

  void TrimCacheV2(bool empty);
  void TrimDeleted(bool empty);

  bool NodeIsOldEnough(CacheRankingsBlock* node, int list);
  int SelectListByLength(Rankings::ScopedRankingsBlock* next);
  void ReportListStats();

  BackendImpl* backend_;
  Rankings* rankings_;
  IndexHeader* header_;
  int max_size_;
  int trim_delays_;
  int index_size_;
  bool new_eviction_;
  bool first_trim_;
  bool trimming_;
  bool delay_trim_;
  bool init_;
  bool test_mode_;
  base::WeakPtrFactory<Eviction> ptr_factory_;

  DISALLOW_COPY_AND_ASSIGN(Eviction);
};

}  // namespace disk_cache

#endif  // NET_DISK_CACHE_EVICTION_H_