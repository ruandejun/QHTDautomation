//
//  AppData.swift
//  PancakeStore
//
//  Created by lunginspector on 2/25/26.
//

import SwiftUI

final class AppData: ObservableObject {
    static let shared = AppData()
    
    @Published var applicationIcon: String = "xmark.circle.fill"
    @Published var applicationIconColor: Color = .secondary
    @Published var applicationStatus: String = "Not logged in!"
    
    @Published var appBundleID: String = ""
    @Published var appVersion: String = ""
    
    @Published var hasAppBeenServed: Bool = false
    
    @Published var ipaTool: IPATool?
    
    @Published var appleId: String = ""
    @Published var password: String = ""
    @Published var code: String = ""
    
    @Published var isAuthenticated: Bool = false
    @Published var isDowngrading: Bool = false
    
    @Published var appLink: String = ""
    
    @Published var hasSent2FACode: Bool = false
    
    @Published var showPassword: Bool = false
}

