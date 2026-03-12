'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import { apiGet } from '@/lib/api';
import { useRun } from '@/components/RunContext';

const NODE_LIMIT = 200;

function nodeColor(topicCoverage) {
  if (topicCoverage === 'your') return '#22c55e';
  if (topicCoverage === 'competitor') return '#ef4444';
  return '#3b82f6';
}

export default function GraphCanvas() {
  const containerRef = useRef(null);
  const rendererRef = useRef(null);
  const { runId } = useRun();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [edgeThreshold, setEdgeThreshold] = useState(0);
  const [zoomLevel, setZoomLevel] = useState('topics');

  const coverageMap = useRef({});

  const cleanup = () => {
    if (rendererRef.current) {
      rendererRef.current.kill();
      rendererRef.current = null;
    }
  };

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    cleanup();

    Promise.all([apiGet('/topic-graph', { runId }), apiGet('/coverage', { runId })])
      .then(([graphData, coverageData]) => {
        if (!mounted || !containerRef.current) return;

        coverageMap.current = (coverageData?.topics || []).reduce((acc, item) => {
          const domains = item.domains || [];
          const sorted = [...domains].sort((a, b) => (b.article_count || 0) - (a.article_count || 0));
          if (!sorted.length) {
            acc[item.topic_id] = 'mixed';
          } else if (sorted[0]?.is_you) {
            acc[item.topic_id] = 'your';
          } else if (sorted.length > 1 && sorted[0].article_count === sorted[1].article_count) {
            acc[item.topic_id] = 'mixed';
          } else {
            acc[item.topic_id] = 'competitor';
          }
          return acc;
        }, {});

        const graph = new Graph();
        const trimmedNodes = (graphData?.nodes || []).slice(0, NODE_LIMIT);
        const nodeSet = new Set(trimmedNodes.map((n) => String(n.id)));

        trimmedNodes.forEach((node) => {
          graph.addNode(String(node.id), {
            label: node.label,
            size: node.size || 4,
            color: nodeColor(coverageMap.current[node.id])
          });
        });

        (graphData?.edges || []).forEach((edge) => {
          if (!nodeSet.has(String(edge.source)) || !nodeSet.has(String(edge.target))) return;
          if ((edge.weight || 0) < edgeThreshold) return;
          const key = `${edge.source}-${edge.target}`;
          if (!graph.hasEdge(key)) {
            graph.addEdgeWithKey(key, String(edge.source), String(edge.target), {
              size: edge.weight || 1,
              color: '#64748b'
            });
          }
        });

        forceAtlas2.assign(graph, { iterations: 100, settings: { gravity: 1 } });

        const renderer = new Sigma(graph, containerRef.current);
        renderer.on('clickNode', ({ node }) => {
          const selectedAttrs = graph.getNodeAttributes(node);
          graph.forEachNode((n) => {
            const connected = graph.neighbors(node).includes(n) || n === node;
            graph.setNodeAttribute(n, 'size', n === node ? (selectedAttrs.size || 4) * 1.8 : 3);
            graph.setNodeAttribute(n, 'color', connected ? graph.getNodeAttribute(n, 'color') : '#1e293b');
          });
          window.dispatchEvent(new CustomEvent('topicSelected', { detail: { id: node, ...selectedAttrs } }));
          renderer.refresh();
        });

        renderer.getCamera().on('updated', () => {
          const ratio = renderer.getCamera().ratio;
          if (ratio > 1.6) setZoomLevel('clusters');
          else if (ratio > 0.7) setZoomLevel('topics');
          else setZoomLevel('articles');
        });

        rendererRef.current = renderer;
      })
      .catch((err) => {
        if (mounted) setError(err);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
      cleanup();
    };
  }, [runId, edgeThreshold]);

  const zoomLabel = useMemo(() => `Zoom detail: ${zoomLevel}`, [zoomLevel]);

  return (
    <section className="panel p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-semibold">Topic Universe Graph</h2>
        <p className="text-xs text-slate-400">{zoomLabel}</p>
      </div>
      <div className="mb-2 flex items-center gap-2 text-sm">
        <label htmlFor="edge-threshold">Edge threshold</label>
        <input
          id="edge-threshold"
          type="range"
          min="0"
          max="10"
          value={edgeThreshold}
          onChange={(event) => setEdgeThreshold(Number(event.target.value))}
        />
        <span>{edgeThreshold}</span>
      </div>
      {loading && <p className="text-sm text-slate-400">Loading...</p>}
      {error && <p className="text-sm text-red-300">API unavailable</p>}
      <div ref={containerRef} className="h-[560px] w-full rounded bg-slate-950" />
    </section>
  );
}
