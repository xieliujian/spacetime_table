// Auto Generated - DO NOT EDIT
// Source: skill.xlsx
using System;
using System.Collections.Generic;
using UnityEngine;

namespace ST.Table
{
    /// <summary>
    /// Skill 表管理器（自动生成）
    /// </summary>
    public partial class TD_SkillTable
    {
        Dictionary<int, TD_Skill> m_DataDict = new();
        List<TD_Skill> m_DataList = new();

        public Dictionary<int, TD_Skill> dataDict => m_DataDict;
        public List<TD_Skill> dataList => m_DataList;

        public TD_Skill GetById(int id)
        {
            m_DataDict.TryGetValue(id, out var data);
            return data;
        }

        public void ParseFromBin(DataStreamReader reader, int rowCount)
        {
            for (int i = 0; i < rowCount; i++)
            {
                var data = new TD_Skill();
                data.ParseFromBin(reader);
                m_DataList.Add(data);
                m_DataDict[data.id] = data;
            }
        }

        public void ParseFromTxt(string content)
        {
            var lines = content.Split('\n');
            for (int i = 3; i < lines.Length; i++)
            {
                var line = lines[i].TrimEnd('\r');
                if (string.IsNullOrEmpty(line)) continue;
                var fields = line.Split('\t');
                var data = new TD_Skill();
                data.ParseFromTxt(fields);
                m_DataList.Add(data);
                m_DataDict[data.id] = data;
            }
        }

        public void Clear()
        {
            m_DataDict.Clear();
            m_DataList.Clear();
        }

        public void Load(string _dir, bool _useBin = true)
        {
            Clear();
            if (_useBin)
            {
                byte[] bytes = TableLoader.LoadBytes(System.IO.Path.Combine(_dir, "skill.bin"));
                var stbl = new StblReader(bytes);
                ParseFromBin(stbl.reader, stbl.rowCount);
            }
            else
            {
                string content = TableLoader.LoadText(System.IO.Path.Combine(_dir, "skill.txt"));
                ParseFromTxt(content);
            }
        }
    }
}
